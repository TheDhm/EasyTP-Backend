"""Kubernetes deployment, service, and ingress operations."""

import os

from django.conf import settings
from kubernetes import client
from kubernetes.client.rest import ApiException

from main.utils.cloudflare_turn import generate_turn_credentials

from .config import load_k8s_config


def create_service(pod_name, app_name):
    """Create a ClusterIP service for the pod."""
    load_k8s_config()

    api_instance = client.CoreV1Api()

    manifest = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {"name": app_name + "-service-" + pod_name, "labels": {"serviceApp": pod_name}},
        "spec": {
            "selector": {"appDep": pod_name},
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 8080,
                    "targetPort": 8080,
                }
            ],
            "type": "ClusterIP",
        },
    }

    try:
        _api_response = api_instance.create_namespaced_service(
            namespace="apps", body=manifest, pretty="true"
        )
    except ApiException as e:
        print("Exception when calling CoreV1Api->create_namespaced_service: %s\n" % e)


def create_ingress(pod_name, app_name, user_hostname, domain="melekabderrahmane.com"):
    """Create Ingress for noVNC access."""
    load_k8s_config()

    networking_api = client.NetworkingV1Api()

    # Create unique subdomain for each user's app
    host = f"{user_hostname}-{app_name}.{domain}"
    service_name = f"{app_name}-service-{pod_name}"

    manifest = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": f"{app_name}-ingress-{pod_name}",
            "namespace": "apps",
            "labels": {"ingressApp": pod_name},
            "annotations": {
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
                "nginx.ingress.kubernetes.io/websocket-services": service_name,
                # For Cloudflare compatibility
                "nginx.ingress.kubernetes.io/use-forwarded-headers": "true",
                "nginx.ingress.kubernetes.io/force-ssl-redirect": "true",
                # Cloudflare Authenticated Origin Pulls (mTLS second gate):
                # require CF's client cert at the TLS handshake. TLSOption +
                # CA Secret live in EasyTP-Infra apps/user-apps/. Without this
                # annotation, the ingress would skip the AOP gate and rely
                # solely on the IPAllowList middleware on Traefik's default
                # router.
                "traefik.ingress.kubernetes.io/router.tls.options": "apps-require-cf-client-cert@kubernetescrd",
                # For noVNC WebSocket support with Cloudflare
                "nginx.ingress.kubernetes.io/configuration-snippet": """
                    proxy_set_header Upgrade $http_upgrade;
                    proxy_set_header Connection "upgrade";
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    # Handle Cloudflare headers
                    proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
                    proxy_set_header CF-Ray $http_cf_ray;
                    # Prevent browser caching of noVNC files (recommended by noVNC docs)
                    add_header Cache-Control "no-cache, no-store, must-revalidate" always;
                    add_header Pragma "no-cache" always;
                    add_header Expires "0" always;
                """,
            },
        },
        "spec": {
            "rules": [
                {
                    "host": host,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {"name": service_name, "port": {"number": 8080}}
                                },
                            }
                        ]
                    },
                }
            ]
        },
    }

    try:
        _api_response = networking_api.create_namespaced_ingress(namespace="apps", body=manifest)
        return host  # Return the host URL
    except ApiException as e:
        print("Exception when calling NetworkingV1Api->create_namespaced_ingress: %s\n" % e)
        return None


def delete_ingress(pod_name, app_name):
    """Delete ingress when stopping pod."""
    load_k8s_config()

    networking_api = client.NetworkingV1Api()

    try:
        networking_api.delete_namespaced_ingress(
            name=f"{app_name}-ingress-{pod_name}", namespace="apps"
        )
    except ApiException as e:
        print("Exception when deleting ingress: %s\n" % e)


def deploy_app(
    username,
    pod_name,
    app_name,
    image,
    vnc_password,
    user_hostname,
    readonly=False,
    app_type="novnc",
    *args,
    **kwargs,
):
    """Deploy a pod with the specified application.

    ``app_type`` selects the container shape:
    - ``"novnc"`` (default): the original noVNC layout, injecting ``VNC_PW``.
    - ``"webrtc"``: a Selkies/WebRTC app that serves its own UI on port 8080. It needs
      Selkies stream-tuning env, HTTP basic auth (reusing the per-pod password), more CPU
      for software x264 encoding, a tmpfs ``/dev/shm`` for Chromium, and a writable saves dir.
    Service + Ingress are shared and unchanged (Selkies also listens on 8080).
    """
    load_k8s_config()

    apps_api = client.AppsV1Api()
    user_space = username

    user_hostname = user_hostname.replace("_", "-")  # "_" not allowed in kubernetes hostname

    # Always pull from our registry; never fall back to a bare (Docker Hub) name.
    full_image = f"{settings.REGISTRY_URL}/{image}"

    # --- Per-type container configuration -------------------------------------------------
    volumes = [
        {
            "name": "nfs-kube",
            "hostPath": {
                "path": "/opt/django-shared/USERDATA",
                "type": "DirectoryOrCreate",
            },
        },
        {
            "name": "nfs-kube-readonly",
            "hostPath": {
                "path": "/opt/django-shared/READONLY",
                "type": "DirectoryOrCreate",
            },
        },
    ]

    if app_type == "webrtc":
        # Selkies streams its own WebRTC UI on 8080; protect it with HTTP basic auth using
        # the same per-pod password the noVNC apps use as VNC_PW.
        env = [
            {"name": "USER_HOSTNAME", "value": user_hostname},
            {"name": "SELKIES_ENCODER", "value": "x264enc"},
            {"name": "SELKIES_FRAMERATE", "value": "30"},
            {"name": "SELKIES_VIDEO_BITRATE", "value": "3000"},
            {"name": "SELKIES_CONGESTION_CONTROL", "value": "true"},
            {"name": "SELKIES_ENABLE_BASIC_AUTH", "value": "true"},
            {"name": "SELKIES_BASIC_AUTH_USER", "value": username},
            {"name": "SELKIES_BASIC_AUTH_PASSWORD", "value": vnc_password},
        ]
        # WebRTC media is peer-to-peer UDP and does NOT cross the ingress; behind the
        # k3s pod NAT, ICE needs a TURN relay or the stream never starts. We use
        # Cloudflare Realtime TURN (managed) so media rides Cloudflare's network and the
        # node's public IP is never exposed: mint short-lived credentials per deploy and
        # point Selkies at turn.cloudflare.com. selkies-gstreamer reads these SELKIES_TURN_*
        # vars natively. Only injected when credentials are minted, so missing/failed CF
        # config degrades gracefully instead of breaking the deploy.
        turn_creds = generate_turn_credentials()
        if turn_creds:
            turn_username, turn_password = turn_creds
            env += [
                {"name": "SELKIES_TURN_HOST", "value": "turn.cloudflare.com"},
                {"name": "SELKIES_TURN_PORT", "value": os.environ.get("SELKIES_TURN_PORT", "3478")},
                {
                    "name": "SELKIES_TURN_PROTOCOL",
                    "value": os.environ.get("SELKIES_TURN_PROTOCOL", "udp"),
                },
                {"name": "SELKIES_TURN_USERNAME", "value": turn_username},
                {"name": "SELKIES_TURN_PASSWORD", "value": turn_password},
            ]
        # Software x264 at 30fps is CPU-heavy; the noVNC 700m limit is far too low.
        resources = {
            "limits": {"ephemeral-storage": "200Mi", "cpu": "3", "memory": "2Gi"},
            "requests": {"ephemeral-storage": "100Mi", "cpu": "1500m", "memory": "1Gi"},
        }
        # Chromium needs a large /dev/shm (mirrors compose shm_size: 512m).
        volumes.append({"name": "dshm", "emptyDir": {"medium": "Memory", "sizeLimit": "512Mi"}})
        volume_mounts = [
            {"name": "dshm", "mountPath": "/dev/shm"},
            # Persist player progress across pod recycles (compose ../data/saves bind mount).
            # Same NFS dir is also visible under /data/myData/socialempires-saves below.
            {
                "name": "nfs-kube",
                "mountPath": "/opt/socialemperors/saves",
                "subPath": f"{user_space}/socialempires-saves",
            },
            # Mount the user's full storage like the noVNC apps so the in-container
            # file manager (thunar) can browse it and open the save files.
            {"name": "nfs-kube", "mountPath": "/data/myData", "subPath": user_space},
            {
                "name": "nfs-kube-readonly",
                "mountPath": "/data/readonly",
                "readOnly": readonly,
            },
        ]
        security_context = {"allowPrivilegeEscalation": False}
    else:
        env = [
            {"name": "VNC_PW", "value": vnc_password},
            {"name": "USER_HOSTNAME", "value": user_hostname},
        ]
        resources = {
            "limits": {"ephemeral-storage": "100Mi", "cpu": "700m", "memory": "512Mi"},
            "requests": {"ephemeral-storage": "50Mi", "cpu": "600m", "memory": "400Mi"},
        }
        volume_mounts = [
            {"name": "nfs-kube", "mountPath": "/data/myData", "subPath": user_space},
            {"name": "nfs-kube-readonly", "mountPath": "/data/readonly", "readOnly": readonly},
        ]
        security_context = None

    container = {
        "name": app_name,
        "image": full_image,
        "imagePullPolicy": "IfNotPresent",
        "ports": [{"containerPort": 8080}],
        "resources": resources,
        "env": env,
        "volumeMounts": volume_mounts,
    }
    if security_context:
        container["securityContext"] = security_context

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": app_name + "-deployment-" + pod_name,
            "labels": {"deploymentApp": pod_name},
        },
        "spec": {
            "selector": {
                "matchLabels": {"app": app_name},
            },
            "replicas": 1,
            "template": {
                "metadata": {"labels": {"app": app_name, "appDep": pod_name}},
                "spec": {
                    "hostname": user_hostname,
                    "containers": [container],
                    "volumes": volumes,
                    "imagePullSecrets": [{"name": "registry-pull-secret"}],
                },
            },
        },
    }

    try:
        apps_api.create_namespaced_deployment(namespace="apps", body=deployment)
    except ApiException as e:
        print("error while deploying: ", e)

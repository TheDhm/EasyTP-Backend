"""Kubernetes deployment, service, and ingress operations."""
from kubernetes import client
from kubernetes.client.rest import ApiException
from .config import load_k8s_config


def create_service(pod_name, app_name):
    """Create a ClusterIP service for the pod."""
    load_k8s_config()

    api_instance = client.CoreV1Api()

    manifest = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": app_name + "-service-" + pod_name,
            "labels": {"serviceApp": pod_name}
        },
        "spec": {
            "selector": {
                "appDep": pod_name
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 8080,
                    "targetPort": 8080,
                }
            ],
            "type": "ClusterIP"
        }
    }

    try:
        api_response = api_instance.create_namespaced_service(
            namespace='apps', body=manifest, pretty='true'
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
                """
            }
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
                                    "service": {
                                        "name": service_name,
                                        "port": {
                                            "number": 8080
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    try:
        api_response = networking_api.create_namespaced_ingress(
            namespace='apps', body=manifest
        )
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
            name=f"{app_name}-ingress-{pod_name}",
            namespace="apps"
        )
    except ApiException as e:
        print("Exception when deleting ingress: %s\n" % e)


def deploy_app(username, pod_name, app_name, image, vnc_password, user_hostname, readonly=False, *args, **kwargs):
    """Deploy a pod with the specified application."""
    load_k8s_config()

    apps_api = client.AppsV1Api()
    user_space = username

    user_hostname = user_hostname.replace('_', '-')  # "_" not allowed in kubernetes hostname

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": app_name + "-deployment-" + pod_name,
            "labels": {
                "deploymentApp": pod_name
            }
        },
        "spec": {
            "selector": {
                "matchLabels": {
                    "app": app_name
                },
            },
            "replicas": 1,
            "template": {
                "metadata": {
                    "labels": {
                        "app": app_name,
                        "appDep": pod_name
                    }
                },
                "spec": {
                    "hostname": user_hostname,
                    "containers": [
                        {
                            "name": app_name,
                            "image": image,
                            "imagePullPolicy": "Never",
                            "ports": [
                                {
                                    "containerPort": 8080
                                }
                            ],
                            "resources": {
                                "limits": {
                                    "ephemeral-storage": "100Mi",
                                    "cpu": "700m",
                                    "memory": "512Mi"
                                },
                                "requests": {
                                    "ephemeral-storage": "50Mi",
                                    "cpu": "600m",
                                    "memory": "400Mi"
                                }
                            },
                            "env": [
                                {
                                    "name": "VNC_PW",
                                    "value": vnc_password
                                },
                                {
                                    "name": "USER_HOSTNAME",
                                    "value": user_hostname
                                }
                            ],
                            "volumeMounts": [
                                {
                                    "name": "nfs-kube",
                                    "mountPath": "/data/myData",
                                    "subPath": user_space
                                },
                                {
                                    "name": "nfs-kube-readonly",
                                    "mountPath": "/data/readonly",
                                    "readOnly": readonly,
                                }
                            ]
                        }
                    ],
                    "volumes": [
                        {
                            "name": "nfs-kube",
                            "hostPath": {
                                "path": "/opt/django-shared/USERDATA",
                                "type": "DirectoryOrCreate"
                            }
                        },
                        {
                            "name": "nfs-kube-readonly",
                            "hostPath": {
                                "path": "/opt/django-shared/READONLY",
                                "type": "DirectoryOrCreate"
                            }
                        }
                    ]
                }
            }
        }
    }

    try:
        apps_api.create_namespaced_deployment(namespace="apps", body=deployment)
    except ApiException as e:
        print("error while deploying: ", e)
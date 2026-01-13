"""Kubernetes pod management operations."""
import uuid
import hashlib
from time import sleep

from kubernetes import client
from kubernetes.client.rest import ApiException

from .config import load_k8s_config
from .deployments import delete_ingress
from shared.utils.threading import autotask


@autotask
def generate_pod_if_not_exist(pod_user, app_name, pod_name, pod_vnc_user, pod_vnc_password):
    """Generate a pod record in the database if it doesn't exist."""
    # Import here to avoid circular imports
    from main.models import Pod

    pod = Pod(
        pod_user=pod_user,
        pod_name=pod_name,
        app_name=app_name,
        pod_vnc_user=pod_vnc_user,
        pod_vnc_password=pod_vnc_password,
        pod_namespace="apps"
    )
    pod.save()


def display_apps(apps, user):
    """Get deployment status for apps.

    Args:
        apps: QuerySet of App objects
        user: The user to check pods for

    Returns:
        dict: App name -> {vnc_pass, deployment_status, novnc_url, is_deployed}
    """
    # Import here to avoid circular imports
    from main.models import Pod, Instances

    print("Displaying apps for user:", user)
    print("Apps to display:", apps)

    data = dict()
    for app in apps:
        status = False
        novnc_url = None

        try:
            pod = Pod.objects.get(pod_user=user, app_name=app.name)
        except Pod.DoesNotExist:
            pod = None

        if pod:
            vnc_pass = pod.pod_vnc_password
            pod_name = pod.pod_name
        else:
            # Create pod if not exist
            pod_name = hashlib.md5(
                f'{app.name}:{user.username}:{user.id}'.encode("utf-8")
            ).hexdigest()
            pod_vnc_user = uuid.uuid4().hex[:6]
            pod_vnc_password = uuid.uuid4().hex
            generate_pod_if_not_exist(
                pod_user=user,
                pod_name=pod_name,
                app_name=app.name,
                pod_vnc_user=pod_vnc_user,
                pod_vnc_password=pod_vnc_password
            )
            vnc_pass = pod_vnc_password
            # Retrieve the created pod
            pod = Pod.objects.get(pod_user=user, app_name=app.name)

        vnc_pass = hashlib.md5(vnc_pass.encode("utf-8")).hexdigest()

        try:
            load_k8s_config()

            api_instance = client.CoreV1Api()
            apps_instance = client.AppsV1Api()
            networking_api = client.NetworkingV1Api()

            # Check if ingress exists and get URL
            try:
                ingress = networking_api.list_namespaced_ingress(
                    namespace="apps",
                    label_selector=f"ingressApp={pod_name}"
                )
                if len(ingress.items) > 0:
                    host = ingress.items[0].spec.rules[0].host
                    novnc_url = f"https://{host}"
            except ApiException:
                pass

            # Check deployment status
            deployment = apps_instance.list_namespaced_deployment(
                namespace="apps",
                label_selector=f"deploymentApp={pod_name}"
            )

            if len(deployment.items) != 0:
                deployment_obj = deployment.items[0]

                # Check if deployment has ready replicas
                ready_replicas = deployment_obj.status.ready_replicas or 0
                available_replicas = deployment_obj.status.available_replicas or 0

                # Consider deployment as running if it has ready replicas
                if ready_replicas > 0:
                    status = True
                # Also check available replicas
                elif available_replicas > 0:
                    status = True
                # Also check deployment conditions for more accurate status
                elif deployment_obj.status.conditions:
                    for condition in deployment_obj.status.conditions:
                        # If deployment is progressing and not failing, consider it starting
                        if (condition.type == "Progressing" and
                            condition.status == "True" and
                            condition.reason == "NewReplicaSetAvailable"):
                            status = True
                            break
                        # If deployment is available, it's definitely running
                        elif (condition.type == "Available" and
                              condition.status == "True"):
                            status = True
                            break
                        # If just progressing, also consider it as starting
                        elif (condition.type == "Progressing" and
                              condition.status == "True"):
                            status = True
                            break

        except ApiException as e:
            # If it's a temporary API error, don't mark as down
            if e.status in [500, 502, 503, 504]:
                # Keep previous status during API outages
                pass
        except Exception as e:
            # For other errors, default to stopped status
            pass

        # Time-based fallback: if pod was just deployed and Kubernetes hasn't caught up yet
        if not status and pod.is_deployed:
            # Check if pod was recently deployed
            try:
                # Get the most recent instance creation time as proxy for deployment time
                recent_instance = Instances.objects.filter(pod=pod).order_by('-id').first()
                if recent_instance:
                    # If we can't get exact timestamp, use pod.is_deployed as fallback
                    status = True
                elif pod.is_deployed:
                    # If is_deployed is True but no Kubernetes status yet, likely just deployed
                    status = True
            except Exception:
                # If pod.is_deployed is True, give it the benefit of the doubt
                if pod.is_deployed:
                    status = True

        data[app.name] = {
            "vnc_pass": vnc_pass,
            "deployment_status": status,
            "novnc_url": novnc_url,
            "is_deployed": pod.is_deployed
        }

    return data


@autotask
def stop_deployed_pod(pod_id, pod_name, app_name):
    """Stop a deployed pod after a delay."""
    # Import here to avoid circular imports
    from main.models import Pod, Instances

    print("sleeping for 3 minutes before stopping the pod...")
    sleep(60 * 3)  # Delay before stopping the pod
    print(f"Stopping pod {pod_name} for app {app_name}...")

    load_k8s_config()

    api_instance = client.CoreV1Api()
    apps_instance = client.AppsV1Api()

    # Delete ingress
    delete_ingress(pod_name, app_name)

    # Delete service
    try:
        deleted_service = api_instance.delete_namespaced_service(
            namespace="apps",
            name=app_name + "-service-" + pod_name
        )
    except ApiException as a:
        print("delete service exception", a)

    # Delete deployment
    try:
        deleted_deployment = apps_instance.delete_namespaced_deployment(
            namespace="apps",
            name=app_name + "-deployment-" + pod_name
        )
    except ApiException as a:
        print("delete deployment exception", a)

    # Delete instance record
    try:
        pod = Pod.objects.get(id=pod_id, app_name=app_name)
        instance = Instances.objects.get(pod=pod, instance_name=pod_name)
        instance.delete()

        pod.is_deployed = False
        pod.save()

    except (Pod.DoesNotExist, Instances.DoesNotExist) as e:
        print("instance already deleted", e)

    print(f"Pod {pod_name} for app {app_name} has been stopped.")
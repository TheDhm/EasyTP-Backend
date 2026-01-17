"""Kubernetes pod management operations."""

import hashlib
import uuid
from time import sleep

from kubernetes import client
from kubernetes.client.rest import ApiException

from shared.utils.threading import autotask

from .config import load_k8s_config
from .deployments import delete_ingress


def get_deployment_stages(pod_name, namespace="apps"):
    """Get detailed deployment status for all K8s resources.

    Returns a dict with status for each deployment stage:
    - deployment: pending | creating | ready | error
    - pod: pending | creating | running | error
    - service: pending | ready | error
    - ingress: pending | creating | ready | error
    """
    stages = {
        "deployment": "pending",
        "pod": "pending",
        "service": "pending",
        "ingress": "pending",
    }

    try:
        load_k8s_config()
        apps_api = client.AppsV1Api()
        core_api = client.CoreV1Api()
        networking_api = client.NetworkingV1Api()

        # Check Deployment status
        try:
            deployments = apps_api.list_namespaced_deployment(
                namespace=namespace, label_selector=f"deploymentApp={pod_name}"
            )
            if deployments.items:
                dep = deployments.items[0]
                ready_replicas = dep.status.ready_replicas or 0
                replicas = dep.status.replicas or 0

                if ready_replicas > 0:
                    stages["deployment"] = "ready"
                elif replicas > 0:
                    stages["deployment"] = "creating"
                else:
                    # Check conditions for more details
                    if dep.status.conditions:
                        for condition in dep.status.conditions:
                            if condition.type == "Progressing" and condition.status == "True":
                                stages["deployment"] = "creating"
                                break
                            elif condition.type == "ReplicaFailure" and condition.status == "True":
                                stages["deployment"] = "error"
                                break
        except ApiException:
            pass

        # Check Pod status
        try:
            pods = core_api.list_namespaced_pod(
                namespace=namespace, label_selector=f"appDep={pod_name}"
            )
            if pods.items:
                pod = pods.items[0]
                phase = pod.status.phase

                if phase == "Running":
                    # Check if all containers are ready
                    if pod.status.container_statuses:
                        all_ready = all(c.ready for c in pod.status.container_statuses)
                        if all_ready:
                            stages["pod"] = "running"
                        else:
                            stages["pod"] = "creating"
                    else:
                        stages["pod"] = "creating"
                elif phase == "Pending":
                    stages["pod"] = "creating"
                elif phase in ["Failed", "Unknown"]:
                    stages["pod"] = "error"
                elif phase == "Succeeded":
                    # For jobs/completed pods
                    stages["pod"] = "running"
        except ApiException:
            pass

        # Check Service has endpoints
        try:
            endpoints = core_api.list_namespaced_endpoints(
                namespace=namespace, label_selector=f"serviceApp={pod_name}"
            )
            if endpoints.items:
                ep = endpoints.items[0]
                # Check if endpoints has subsets with addresses
                if ep.subsets and any(
                    subset.addresses for subset in ep.subsets if subset.addresses
                ):
                    stages["service"] = "ready"
                else:
                    # Service exists but no endpoints yet
                    stages["service"] = "pending"
        except ApiException:
            pass

        # Check Ingress status
        try:
            ingresses = networking_api.list_namespaced_ingress(
                namespace=namespace, label_selector=f"ingressApp={pod_name}"
            )
            if ingresses.items:
                ingress = ingresses.items[0]
                # Check if ingress has been configured by the controller
                if ingress.status.load_balancer and ingress.status.load_balancer.ingress:
                    stages["ingress"] = "ready"
                else:
                    stages["ingress"] = "creating"
        except ApiException:
            pass

    except Exception:
        # If we can't connect to K8s, return pending for all
        pass

    return stages


def compute_overall_status(stages):
    """Compute overall status and message from deployment stages.

    Returns:
        tuple: (status, message, ready)
        - status: "starting" | "running" | "stopped" | "error"
        - message: Human-readable status message
        - ready: True if all stages are complete
    """
    # Check for any errors
    error_stages = [k for k, v in stages.items() if v == "error"]
    if error_stages:
        return (
            "error",
            f"Error in {', '.join(error_stages)}",
            False,
        )

    # Check if all stages are ready
    all_ready = all(v in ["ready", "running"] for v in stages.values())
    if all_ready:
        return ("running", "Application is running", True)

    # Check if nothing has started
    all_pending = all(v == "pending" for v in stages.values())
    if all_pending:
        return ("stopped", "Application is stopped", False)

    # Something is in progress - determine message
    if stages["deployment"] == "creating":
        return ("starting", "Creating deployment...", False)
    elif stages["pod"] == "creating":
        return ("starting", "Starting container...", False)
    elif stages["service"] == "pending":
        return ("starting", "Configuring network...", False)
    elif stages["ingress"] == "creating":
        return ("starting", "Setting up routing...", False)
    else:
        return ("starting", "Deployment in progress...", False)


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
        pod_namespace="apps",
    )
    pod.save()


def display_apps(apps, user):
    """Get deployment status for apps with granular stage information.

    Args:
        apps: QuerySet of App objects
        user: The user to check pods for

    Returns:
        dict: App name -> {
            vnc_pass, deployment_status, novnc_url, is_deployed,
            status, stages, message, ready
        }
    """
    # Import here to avoid circular imports
    from main.models import Pod

    print("Displaying apps for user:", user)
    print("Apps to display:", apps)

    data = dict()
    for app in apps:
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
                f"{app.name}:{user.username}:{user.id}".encode("utf-8")
            ).hexdigest()
            pod_vnc_user = uuid.uuid4().hex[:6]
            pod_vnc_password = uuid.uuid4().hex
            generate_pod_if_not_exist(
                pod_user=user,
                pod_name=pod_name,
                app_name=app.name,
                pod_vnc_user=pod_vnc_user,
                pod_vnc_password=pod_vnc_password,
            )
            vnc_pass = pod_vnc_password
            # Retrieve the created pod
            pod = Pod.objects.get(pod_user=user, app_name=app.name)

        vnc_pass_hash = hashlib.md5(vnc_pass.encode("utf-8")).hexdigest()

        # Default stages for non-deployed apps
        stages = {
            "deployment": "pending",
            "pod": "pending",
            "service": "pending",
            "ingress": "pending",
        }
        overall_status = "stopped"
        message = "Application is stopped"
        ready = False

        # Only check K8s status if the app is marked as deployed
        if pod.is_deployed:
            try:
                load_k8s_config()
                networking_api = client.NetworkingV1Api()

                # Check if ingress exists and get URL
                try:
                    ingress = networking_api.list_namespaced_ingress(
                        namespace="apps", label_selector=f"ingressApp={pod_name}"
                    )
                    if len(ingress.items) > 0:
                        host = ingress.items[0].spec.rules[0].host
                        novnc_url = f"https://{host}"
                except ApiException:
                    pass

                # Get detailed deployment stages
                stages = get_deployment_stages(pod_name, namespace="apps")
                overall_status, message, ready = compute_overall_status(stages)

            except ApiException as e:
                # If it's a temporary API error, show as starting
                if e.status in [500, 502, 503, 504]:
                    overall_status = "starting"
                    message = "Checking deployment status..."
                    ready = False
            except Exception:
                # For connection errors, show as starting if is_deployed
                overall_status = "starting"
                message = "Connecting to cluster..."
                ready = False

        # For backward compatibility, deployment_status is True only when fully ready
        deployment_status = ready

        data[app.name] = {
            "vnc_pass": vnc_pass_hash,
            "deployment_status": deployment_status,
            "novnc_url": novnc_url,
            "is_deployed": pod.is_deployed,
            # New granular status fields
            "status": overall_status,
            "stages": stages,
            "message": message,
            "ready": ready,
        }

    return data


@autotask
def stop_deployed_pod(pod_id, pod_name, app_name):
    """Stop a deployed pod after a delay."""
    # Import here to avoid circular imports
    from main.models import Instances, Pod

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
        _deleted_service = api_instance.delete_namespaced_service(
            namespace="apps", name=app_name + "-service-" + pod_name
        )
    except ApiException as a:
        print("delete service exception", a)

    # Delete deployment
    try:
        _deleted_deployment = apps_instance.delete_namespaced_deployment(
            namespace="apps", name=app_name + "-deployment-" + pod_name
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

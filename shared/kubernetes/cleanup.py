"""Kubernetes cleanup job operations."""

import logging
from datetime import datetime

from kubernetes import client
from kubernetes.client.rest import ApiException

from .config import load_k8s_config

logger = logging.getLogger(__name__)

CLEANUP_IMAGE = "bitnami/kubectl:latest"
NAMESPACE = "apps"


def create_cleanup_job(pod_name: str, app_name: str, delay_seconds: int = 180) -> str:
    """
    Create a K8s Job that deletes resources after a delay.

    Args:
        pod_name: The pod identifier (hash)
        app_name: Application name (lowercase)
        delay_seconds: Delay before cleanup (default: 180 = 3 minutes)

    Returns:
        str: The job name for tracking/cancellation
    """
    load_k8s_config()
    batch_api = client.BatchV1Api()

    job_name = f"cleanup-{app_name}-{pod_name[:12]}-{int(datetime.now().timestamp())}"

    # Resources to delete
    deployment_name = f"{app_name}-deployment-{pod_name}"
    service_name = f"{app_name}-service-{pod_name}"
    ingress_name = f"{app_name}-ingress-{pod_name}"

    # Command: sleep then delete (kubectl handles missing resources gracefully)
    cleanup_command = (
        f"sleep {delay_seconds} && "
        f"kubectl delete deployment {deployment_name} -n {NAMESPACE} --ignore-not-found && "
        f"kubectl delete service {service_name} -n {NAMESPACE} --ignore-not-found && "
        f"kubectl delete ingress {ingress_name} -n {NAMESPACE} --ignore-not-found"
    )

    job_manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": NAMESPACE,
            "labels": {
                "app": "cleanup-job",
                "target-pod": pod_name,
                "target-app": app_name,
            },
        },
        "spec": {
            "ttlSecondsAfterFinished": 60,  # Auto-delete job 1 min after completion
            "backoffLimit": 1,
            "template": {
                "spec": {
                    "serviceAccountName": "cleanup-job-account",
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "cleanup",
                            "image": CLEANUP_IMAGE,
                            "command": ["/bin/sh", "-c", cleanup_command],
                            "resources": {
                                "requests": {"cpu": "10m", "memory": "32Mi"},
                                "limits": {"cpu": "100m", "memory": "64Mi"},
                            },
                        }
                    ],
                },
            },
        },
    }

    try:
        batch_api.create_namespaced_job(namespace=NAMESPACE, body=job_manifest)
        logger.info(f"Created cleanup job: {job_name}")
        return job_name
    except ApiException as e:
        logger.error(f"Failed to create cleanup job: {e}")
        raise


def delete_cleanup_job(job_name: str) -> bool:
    """
    Delete a cleanup job (cancellation).

    Args:
        job_name: The name of the job to delete

    Returns:
        bool: True if deleted or already gone, False on error
    """
    load_k8s_config()
    batch_api = client.BatchV1Api()

    try:
        batch_api.delete_namespaced_job(
            name=job_name, namespace=NAMESPACE, propagation_policy="Background"
        )
        logger.info(f"Deleted cleanup job: {job_name}")
        return True
    except ApiException as e:
        if e.status == 404:
            logger.info(f"Cleanup job {job_name} already deleted")
            return True
        logger.error(f"Failed to delete cleanup job: {e}")
        return False

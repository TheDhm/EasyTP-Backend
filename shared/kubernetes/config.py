"""Kubernetes configuration utilities."""
from kubernetes import config
from kubernetes.config import ConfigException


def load_k8s_config():
    """Load Kubernetes configuration.

    Attempts to load kubeconfig first (for local development),
    then falls back to in-cluster config (for production).
    """
    try:
        config.load_kube_config()
    except ConfigException:
        config.load_incluster_config()
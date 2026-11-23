"""deploy_app must create the user's storage directory before the pod mounts it."""

import os
from unittest.mock import patch

from shared.kubernetes import deployments


def test_deploy_app_creates_user_directory_first(tmp_path):
    with (
        patch.object(deployments, "USERDATA_ROOT", str(tmp_path)),
        patch.object(deployments, "load_k8s_config"),
        patch.object(deployments.client, "AppsV1Api") as apps_api,
    ):
        created = deployments.deploy_app(
            username="alice",
            pod_name="abc",
            app_name="logisim",
            image="logisim:latest",
            vnc_password="x",
            user_hostname="alice",
        )

    assert created is True
    # Created by this process, so owned by the uid the lab also runs as
    assert os.path.isdir(tmp_path / "alice")
    assert os.stat(tmp_path / "alice").st_uid == os.getuid()
    apps_api.return_value.create_namespaced_deployment.assert_called_once()

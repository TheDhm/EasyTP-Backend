"""Unit tests for main.models module."""
import pytest


@pytest.mark.django_db
class TestDefaultUser:
    """Tests for DefaultUser model."""

    def test_create_user(self):
        """Test creating a regular user."""
        from main.models import DefaultUser, AccessGroup
        group = AccessGroup.objects.create(name='TestGroup')
        user = DefaultUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            group=group,
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert user.is_active
        assert not user.is_superuser

    def test_user_role_default(self):
        """Test user role defaults to STUDENT."""
        from main.models import DefaultUser, AccessGroup
        group = AccessGroup.objects.create(name='TestGroup2')
        user = DefaultUser.objects.create_user(
            username='student',
            email='student@example.com',
            password='pass123',
            group=group,
        )
        assert user.role == DefaultUser.STUDENT

    def test_user_roles(self):
        """Test all user role options."""
        from main.models import DefaultUser
        assert DefaultUser.STUDENT == 'S'
        assert DefaultUser.TEACHER == 'T'
        assert DefaultUser.ADMIN == 'A'
        assert DefaultUser.GUEST == 'G'

    def test_user_upload_limit_default(self):
        """Test default upload limit."""
        from main.models import DefaultUser, AccessGroup
        group = AccessGroup.objects.create(name='TestGroup3')
        user = DefaultUser.objects.create_user(
            username='user',
            email='user@example.com',
            password='pass123',
            group=group,
        )
        assert user.upload_limit == 50  # Default 50 MB

    def test_user_str_representation(self):
        """Test user string representation."""
        from main.models import DefaultUser, AccessGroup
        group = AccessGroup.objects.create(name='TestGroup4')
        user = DefaultUser.objects.create_user(
            username='displayuser',
            email='display@example.com',
            password='pass123',
            group=group,
        )
        assert str(user) == 'displayuser'


@pytest.mark.django_db
class TestAccessGroup:
    """Tests for AccessGroup model."""

    def test_create_group(self):
        """Test creating an access group."""
        from main.models import AccessGroup
        group = AccessGroup.objects.create(name='Engineering')
        assert group.name == 'Engineering'

    def test_group_constants(self):
        """Test group constant values."""
        from main.models import AccessGroup
        assert AccessGroup.FULL == 'Full Access Group'
        assert AccessGroup.GUEST == 'Guest'

    def test_group_str_representation(self):
        """Test group string representation."""
        from main.models import AccessGroup
        group = AccessGroup.objects.create(name='Science')
        assert str(group) == 'Science'


@pytest.mark.django_db
class TestApp:
    """Tests for App model."""

    def test_create_app(self):
        """Test creating an app."""
        from main.models import App
        app = App.objects.create(
            name='logisim',
            image='logisim:latest',
        )
        assert app.name == 'logisim'
        assert app.image == 'logisim:latest'

    def test_app_str_representation(self):
        """Test app string representation."""
        from main.models import App
        app = App.objects.create(name='gns3', image='gns3:latest')
        assert str(app) == 'gns3'

    def test_app_with_groups(self):
        """Test app association with access groups."""
        from main.models import AccessGroup, App
        group1 = AccessGroup.objects.create(name='Group1')
        group2 = AccessGroup.objects.create(name='Group2')
        app = App.objects.create(name='testapp', image='test:latest')

        # group1.apps.add(app)
        # group2.apps.add(app)

        app.group.set([group1, group2])

        # app.group.set(group1, group2)

        assert group1 in app.group.all()
        assert group2 in app.group.all()
        assert app in group1.apps.all()
        assert app in group2.apps.all()


@pytest.mark.django_db
class TestPod:
    """Tests for Pod model."""

    def test_create_pod(self):
        """Test creating a pod."""
        from main.models import DefaultUser, AccessGroup, Pod
        group = AccessGroup.objects.create(name='PodGroup')
        user = DefaultUser.objects.create_user(
            username='poduser',
            email='pod@example.com',
            password='pass123',
            group=group,
        )
        pod = Pod.objects.create(
            pod_user=user,
            pod_name='test-pod-hash',
            app_name='logisim',
            pod_vnc_user='vncuser',
            pod_vnc_password='vncpass',
            pod_namespace='apps',
        )
        assert pod.pod_user == user
        assert pod.pod_name == 'test-pod-hash'
        assert pod.app_name == 'logisim'
        assert pod.is_deployed == False

    def test_pod_is_deployed_default(self):
        """Test pod is_deployed defaults to False."""
        from main.models import DefaultUser, AccessGroup, Pod
        group = AccessGroup.objects.create(name='PodGroup2')
        user = DefaultUser.objects.create_user(
            username='poduser2',
            email='pod2@example.com',
            password='pass123',
            group=group,
        )
        pod = Pod.objects.create(
            pod_user=user,
            pod_name='test-pod-2',
            app_name='gns3',
            pod_vnc_user='vnc2',
            pod_vnc_password='pass2',
            pod_namespace='apps',
        )
        assert pod.is_deployed == False

    def test_pod_str_representation(self):
        """Test pod string representation."""
        from main.models import DefaultUser, AccessGroup, Pod
        group = AccessGroup.objects.create(name='PodGroup3')
        user = DefaultUser.objects.create_user(
            username='poduser3',
            email='pod3@example.com',
            password='pass123',
            group=group,
        )
        pod = Pod.objects.create(
            pod_user=user,
            pod_name='my-pod-name',
            app_name='testapp',
            pod_vnc_user='vnc3',
            pod_vnc_password='pass3',
            pod_namespace='apps',
        )
        assert 'my-pod-name' in str(pod)
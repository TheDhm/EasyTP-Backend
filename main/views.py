# import binascii
# import random
# from django.shortcuts import render
# import uuid
# from django.shortcuts import render, redirect, reverse
# from django.http import HttpResponse, HttpResponseRedirect
# from django.contrib.auth.forms import AuthenticationForm
# from django.contrib.auth import login, logout, authenticate
# from django.contrib import messages
# from django.conf import settings
# from .models import Pod, App, DefaultUser, AccessGroup, Instances
# import hashlib
# from kubernetes import client
# from kubernetes.client.rest import ApiException
# import os
# import base64
# from .forms import UploadFileForm, PublicUserCreationForm
# import mimetypes
# from django.core.exceptions import SuspiciousOperation
# from django.views.decorators.csrf import csrf_protect
# from django.utils.html import escape
# from django.http import HttpResponse, FileResponse, Http404
# from django.views.decorators.cache import never_cache
# from django.http import JsonResponse
# from .utils.activity_logger import ActivityLogger
# from .models import UserActivity
# from .forms import ActivityFilterForm
# from django.core.paginator import Paginator
# from django.db.models import Q
# from django.utils import timezone
# from datetime import timedelta, datetime

# # Import shared utilities
# from shared.files import (
#     safe_base64_decode,
#     validate_and_sanitize_path,
#     sanitize_filename,
#     get_sub_files_secure,
#     save_file_secure,
#     get_actual_storage_usage,
# )
# from shared.kubernetes import (
#     display_apps,
#     deploy_app,
#     create_service,
#     create_ingress,
#     delete_ingress,
#     stop_deployed_pod,
#     generate_pod_if_not_exist,
#     load_k8s_config,
# )


# app_name = "main"


# NFS_SERVER = os.getenv('NFS_SERVER')
# NFS_PATH = os.getenv('NFS_PATH')


# @autotask
# def generate_pod_if_not_exist(pod_user, app_name, pod_name, pod_vnc_user, pod_vnc_password):
#     pod = Pod(pod_user=pod_user,
#               pod_name=pod_name,
#               app_name=app_name,
#               pod_vnc_user=pod_vnc_user,
#               pod_vnc_password=pod_vnc_password,
#               pod_namespace="apps")
#     pod.save()


# # @autotask
# def create_service(pod_name, app_name):
#     try:
#         config.load_kube_config()
#     except ConfigException:
#         config.load_incluster_config()

#     api_instance = client.CoreV1Api()

#     manifest = {
#         "kind": "Service",
#         "apiVersion": "v1",
#         "metadata": {
#             "name": app_name + "-service-" + pod_name,
#             "labels": {"serviceApp": pod_name}
#         },
#         "spec": {
#             "selector": {
#                 "appDep": pod_name
#             },
#             "ports": [
#                 {
#                     "protocol": "TCP",
#                     "port": 8080,
#                     "targetPort": 8080,
#                 }
#             ],
#             "type": "ClusterIP"
#         }
#     }

#     try:
#         api_response = api_instance.create_namespaced_service(namespace='apps', body=manifest, pretty='true')
#     except ApiException as e:
#         print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)


# # @autotask
# def create_ingress(pod_name, app_name, user_hostname, domain="melekabderrahmane.com"):
#     """Create Ingress for noVNC access"""
#     try:
#         config.load_kube_config()
#     except ConfigException:
#         config.load_incluster_config()

#     networking_api = client.NetworkingV1Api()

#     # Create unique subdomain for each user's app
#     host = f"{user_hostname}-{app_name}.{domain}"
#     service_name = f"{app_name}-service-{pod_name}"

#     manifest = {
#         "apiVersion": "networking.k8s.io/v1",
#         "kind": "Ingress",
#         "metadata": {
#             "name": f"{app_name}-ingress-{pod_name}",
#             "namespace": "apps",
#             "labels": {"ingressApp": pod_name},
#             "annotations": {
#                 "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
#                 "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
#                 "nginx.ingress.kubernetes.io/websocket-services": service_name,
#                 # For Cloudflare compatibility
#                 "nginx.ingress.kubernetes.io/use-forwarded-headers": "true",
#                 "nginx.ingress.kubernetes.io/force-ssl-redirect": "true",
#                 # For noVNC WebSocket support with Cloudflare
#                 "nginx.ingress.kubernetes.io/configuration-snippet": """
#                     proxy_set_header Upgrade $http_upgrade;
#                     proxy_set_header Connection "upgrade";
#                     proxy_set_header Host $host;
#                     proxy_set_header X-Real-IP $remote_addr;
#                     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#                     proxy_set_header X-Forwarded-Proto $scheme;
#                     # Handle Cloudflare headers
#                     proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
#                     proxy_set_header CF-Ray $http_cf_ray;
#                     # Prevent browser caching of noVNC files (recommended by noVNC docs)
#                     add_header Cache-Control "no-cache, no-store, must-revalidate" always;
#                     add_header Pragma "no-cache" always;
#                     add_header Expires "0" always;
#                 """
#             }
#         },
#         "spec": {
#             "rules": [
#                 {
#                     "host": host,
#                     "http": {
#                         "paths": [
#                             {
#                                 "path": "/",
#                                 "pathType": "Prefix",
#                                 "backend": {
#                                     "service": {
#                                         "name": service_name,
#                                         "port": {
#                                             "number": 8080
#                                         }
#                                     }
#                                 }
#                             }
#                         ]
#                     }
#                 }
#             ]
#         }
#     }

#     try:
#         api_response = networking_api.create_namespaced_ingress(namespace='apps', body=manifest)
#         return host  # Return the host URL
#     except ApiException as e:
#         print("Exception when calling NetworkingV1Api->create_namespaced_ingress: %s\n" % e)
#         return None


# def delete_ingress(pod_name, app_name):
#     """Delete ingress when stopping pod"""
#     try:
#         config.load_kube_config()
#     except ConfigException:
#         config.load_incluster_config()

#     networking_api = client.NetworkingV1Api()

#     try:
#         networking_api.delete_namespaced_ingress(
#             name=f"{app_name}-ingress-{pod_name}",
#             namespace="apps"
#         )
#     except ApiException as e:
#         print("Exception when deleting ingress: %s\n" % e)


# # @autotask
# def deploy_app(username, pod_name, app_name, image, vnc_password, user_hostname, readonly=False, *args, **kwargs):
#     try:
#         config.load_kube_config()
#     except ConfigException:
#         config.load_incluster_config()

#     apps_api = client.AppsV1Api()
#     user_space = username

#     user_hostname = user_hostname.replace('_', '-')  # " _ " not allowed in kubernetes hostname

#     deployment = {
#         "apiVersion": "apps/v1",
#         "kind": "Deployment",
#         "metadata": {
#             "name": app_name + "-deployment-" + pod_name,
#             "labels": {
#                 "deploymentApp": pod_name
#             }

#         },
#         "spec": {
#             "selector": {
#                 "matchLabels": {
#                     "app": app_name
#                 },
#             },
#             "replicas": 1,
#             "template": {
#                 "metadata": {
#                     "labels": {
#                         "app": app_name,
#                         "appDep": pod_name
#                     }
#                 },
#                 "spec": {
#                     "hostname": user_hostname,
#                     # "securityContext": {
#                     #     "runAsUser": 1000
#                     # },
#                     "containers": [
#                         {
#                             "name": app_name,
#                             "image": image,
#                             "imagePullPolicy": "Never",
#                             "ports": [
#                                 {
#                                     "containerPort": 8080
#                                 }
#                             ],
#                             "resources": {
#                                 "limits": {
#                                     "ephemeral-storage": "100Mi",
#                                     "cpu": "700m",
#                                     "memory": "512Mi"
#                                 },
#                                 "requests": {
#                                     "ephemeral-storage": "50Mi",
#                                     "cpu": "600m",
#                                     "memory": "400Mi"
#                                 }
#                             },
#                             "env": [
#                                 {
#                                     "name": "VNC_PW",
#                                     "value": vnc_password
#                                 },
#                                 {
#                                     "name": "USER_HOSTNAME",
#                                     "value": user_hostname
#                                 }
#                             ],
#                             "volumeMounts": [
#                                 {
#                                     "name": "nfs-kube",
#                                     "mountPath": "/data/myData",
#                                     "subPath": user_space
#                                 },
#                                 {
#                                     "name": "nfs-kube-readonly",
#                                     "mountPath": "/data/readonly",
#                                     "readOnly": readonly,
#                                 }
#                             ]

#                         }
#                     ],
#                     "volumes": [
#                         {
#                             "name": "nfs-kube",
#                             "hostPath":
#                                 {
#                                     "path": "/opt/django-shared/USERDATA",
#                                     "type": "DirectoryOrCreate"
#                                 }
#                         },
#                         {
#                             "name": "nfs-kube-readonly",
#                             "hostPath":
#                                 {
#                                     "path": "/opt/django-shared/READONLY",
#                                     "type": "DirectoryOrCreate"
#                                 }
#                         }
#                     ]
#                 }
#             }
#         }
#     }
#     try:
#         apps_api.create_namespaced_deployment(namespace="apps", body=deployment)
#     except ApiException as e:
#         print("error while deploying: ", e)

# @never_cache
# def start_pod(request, app_name, user_id=None):
#     """Updated start_pod function"""
#     if request.user.is_authenticated:
#         try:
#             user_id = int(user_id)
#         except:
#             user_id = None

#         readonly_volume = False
#         user = request.user

#         if request.user.role != DefaultUser.STUDENT and request.user.role != DefaultUser.GUEST:
#             if user_id:
#                 try:
#                     user = DefaultUser.objects.get(id=user_id)
#                 except DefaultUser.DoesNotExist:
#                     return redirect(request.META.get('HTTP_REFERER', '/apps'))
#         else:
#             readonly_volume = True

#         try:
#             pod = Pod.objects.get(pod_user=user, app_name=app_name)
#             app = App.objects.get(name=app_name)
#         except (App.DoesNotExist, Pod.DoesNotExist):
#             return redirect(request.META.get('HTTP_REFERER', '/apps'))

#         cleaned_username = user.username.replace('_', '-').replace('.', '-').lower()

#         # Deploy the app
#         deploy_app(username=user.username,
#                 pod_name=pod.pod_name,
#                 app_name=app_name.lower(),
#                 image=app.image,
#                 vnc_password=hashlib.md5(pod.pod_vnc_password.encode("utf-8")).hexdigest(),
#                 user_hostname=cleaned_username,
#                 readonly=readonly_volume)

#         pod.is_deployed = True
#         pod.save()

#         # Create ClusterIP service
#         create_service(pod_name=pod.pod_name, app_name=app_name.lower())

#         # Create Ingress for external access
#         novnc_url = create_ingress(pod_name=pod.pod_name,
#                                   app_name=app_name.lower(),
#                                   user_hostname=cleaned_username)

#         # Store the URL in your model if needed
#         new_instance, created = Instances.objects.get_or_create(pod=pod, instance_name=pod.pod_name)
#         if hasattr(new_instance, 'novnc_url'):
#             new_instance.novnc_url = f"https://{novnc_url}" if novnc_url else None
#             new_instance.save()

#         print("Pod started successfully:", pod.pod_name)

#         ActivityLogger.log_pod_start(user, app_name, pod.pod_name, request)

#         stop_deployed_pod(pod_id=pod.id, pod_name=pod.pod_name, app_name=app_name)

#         # return redirect(request.META.get('HTTP_REFERER', '/apps'))
#         return redirect('main:test_apps')
#     return redirect('main:landpage')


# @never_cache
# def stop_pod(request, app_name, user_id=None):
#     """Updated stop_pod function"""
#     if request.user.is_authenticated:
#         try:
#             user_id = int(user_id)
#         except:
#             user_id = None

#         if user_id and request.user.role != DefaultUser.STUDENT and request.user.role != DefaultUser.GUEST:
#             try:
#                 user = DefaultUser.objects.get(id=user_id)
#             except DefaultUser.DoesNotExist:
#                 return redirect(request.META.get('HTTP_REFERER', '/apps'))
#         else:
#             user = request.user

#         try:
#             pod = Pod.objects.get(pod_user=user, app_name=app_name)
#         except Pod.DoesNotExist:
#             return redirect(request.META.get('HTTP_REFERER', '/apps'))

#         pod_name = pod.pod_name
#         log_app_name = app_name
#         app_name = app_name.lower()

#         try:
#             config.load_kube_config()
#         except ConfigException:
#             config.load_incluster_config()

#         api_instance = client.CoreV1Api()
#         apps_instance = client.AppsV1Api()

#         # Delete ingress
#         delete_ingress(pod_name, app_name)

#         # Delete service
#         try:
#             deleted_service = api_instance.delete_namespaced_service(
#                 namespace="apps",
#                 name=app_name + "-service-" + pod_name
#             )
#         except ApiException as a:
#             print("delete service exception", a)

#         # Delete deployment
#         try:
#             deleted_deployment = apps_instance.delete_namespaced_deployment(
#                 namespace="apps",
#                 name=app_name + "-deployment-" + pod_name
#             )

#             if deleted_deployment.status == "Success":
#                 pod.is_deployed = False
#                 pod.save()

#         except ApiException as a:
#             print("delete deployment exception", a)

#         # Delete instance record
#         try:
#             instance = Instances.objects.get(pod=pod, instance_name=pod_name)
#             instance.delete()
#         except Instances.DoesNotExist as e:
#             print("instance already deleted", e)

#         ActivityLogger.log_pod_stop(user, log_app_name, pod_name, request)

#         return redirect(request.META.get('HTTP_REFERER', '/apps'))
#     return redirect('main:landpage')


# def display_apps(apps, user):
#     """Updated display_apps function"""

#     print("Displaying apps for user:", user)
#     print("Apps to display:", apps)

#     data = dict()
#     for app in apps:
#         status = False
#         novnc_url = None

#         try:
#             pod = Pod.objects.get(pod_user=user, app_name=app.name)
#         except Pod.DoesNotExist:
#             pod = None

#         if pod:
#             vnc_pass = pod.pod_vnc_password
#             pod_name = pod.pod_name
#         else:
#             # Create pod if not exist
#             pod_name = hashlib.md5(
#                 f'{app.name}:{user.username}:{user.id}'.encode("utf-8")).hexdigest()
#             pod_vnc_user = uuid.uuid4().hex[:6]
#             pod_vnc_password = uuid.uuid4().hex
#             generate_pod_if_not_exist(pod_user=user,
#                                       pod_name=pod_name,
#                                       app_name=app.name,
#                                       pod_vnc_user=pod_vnc_user,
#                                       pod_vnc_password=pod_vnc_password)
#             vnc_pass = pod_vnc_password
#             # Retrieve the created pod
#             pod = Pod.objects.get(pod_user=user, app_name=app.name)

#         vnc_pass = hashlib.md5(vnc_pass.encode("utf-8")).hexdigest()

#         try:
#             try:
#                 config.load_kube_config()
#             except ConfigException:
#                 config.load_incluster_config()

#             api_instance = client.CoreV1Api()
#             apps_instance = client.AppsV1Api()
#             networking_api = client.NetworkingV1Api()

#             # Check if ingress exists and get URL
#             try:
#                 ingress = networking_api.list_namespaced_ingress(
#                     namespace="apps",
#                     label_selector=f"ingressApp={pod_name}"
#                 )
#                 if len(ingress.items) > 0:
#                     host = ingress.items[0].spec.rules[0].host
#                     novnc_url = f"https://{host}"
#             except ApiException:
#                 pass

#             # Check deployment status
#             deployment = apps_instance.list_namespaced_deployment(
#                 namespace="apps",
#                 label_selector=f"deploymentApp={pod_name}"
#             )

#             if len(deployment.items) != 0:
#                 deployment_obj = deployment.items[0]

#                 # Check if deployment has ready replicas
#                 ready_replicas = deployment_obj.status.ready_replicas or 0
#                 available_replicas = deployment_obj.status.available_replicas or 0

#                 # Consider deployment as running if it has ready replicas
#                 if ready_replicas > 0:
#                     status = True
#                 # Also check available replicas
#                 elif available_replicas > 0:
#                     status = True
#                 # Also check deployment conditions for more accurate status
#                 elif deployment_obj.status.conditions:
#                     for condition in deployment_obj.status.conditions:
#                         # If deployment is progressing and not failing, consider it starting
#                         if (condition.type == "Progressing" and
#                             condition.status == "True" and
#                             condition.reason == "NewReplicaSetAvailable"):
#                             status = True
#                             break
#                         # If deployment is available, it's definitely running
#                         elif (condition.type == "Available" and
#                               condition.status == "True"):
#                             status = True
#                             break
#                         # If just progressing, also consider it as starting
#                         elif (condition.type == "Progressing" and
#                               condition.status == "True"):
#                             status = True
#                             break

#         except ApiException as e:
#             # If it's a temporary API error, don't mark as down
#             if e.status in [500, 502, 503, 504]:
#                 # Keep previous status during API outages
#                 pass
#         except Exception as e:
#             # For other errors, default to stopped status
#             pass

#         # Time-based fallback: if pod was just deployed and Kubernetes hasn't caught up yet
#         if not status and pod.is_deployed:
#             # Check if pod was recently deployed
#             try:
#                 # Get the most recent instance creation time as proxy for deployment time
#                 recent_instance = Instances.objects.filter(pod=pod).order_by('-id').first()
#                 if recent_instance:
#                     # If we can't get exact timestamp, use pod.is_deployed as fallback
#                     status = True
#                 elif pod.is_deployed:
#                     # If is_deployed is True but no Kubernetes status yet, likely just deployed
#                     status = True
#             except Exception:
#                 # If pod.is_deployed is True, give it the benefit of the doubt
#                 if pod.is_deployed:
#                     status = True

#         data[app.name] = {
#             "vnc_pass": vnc_pass,
#             "deployment_status": status,
#             "novnc_url": novnc_url,
#             "is_deployed": pod.is_deployed
#         }

#     return data


# @never_cache
# def test_apps(request):
#     if request.user.is_authenticated:
#         data = dict()
#         if request.user.role == DefaultUser.TEACHER or request.user.role == DefaultUser.ADMIN:
#             apps = App.objects.all()
#             data = display_apps(apps, request.user)

#         else:
#             user = request.user
#             apps = user.group.apps.all()
#             data = display_apps(apps, user)

#         return render(request, 'main/display_apps.html', {"data": data})
#     return redirect('main:landpage')


# def homepage(request):
#     if request.user.is_authenticated:
#         if request.user.is_superuser or request.user.role == DefaultUser.ADMIN:
#             return render(request, 'main/admin.html')

#         elif request.user.role == DefaultUser.TEACHER:
#             return render(request, 'main/teacher_home.html')

#         elif request.user.role == DefaultUser.STUDENT or request.user.role == DefaultUser.GUEST:
#             return render(request, 'main/student_home.html')

#     return redirect('main:landpage')


# def landpage(request):
#      return render(request, 'main/landing.html')


# def logout_request(request):
#     if request.user.is_authenticated:
#         ActivityLogger.log_logout(request.user, request)
#         logout(request)
#     return redirect("main:landpage")


# def login_request(request):
#     if request.user.is_authenticated:
#         return redirect("main:homepage")

#     if request.method == "POST":
#         form = AuthenticationForm(request=request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get("username")
#             password = form.cleaned_data.get("password")

#             user = authenticate(username=username, password=password)
#             if user is not None:
#                 login(request, user)

#                 ActivityLogger.log_login(user, request)

#                 return redirect("main:homepage")
#             else:
#                 messages.error(request, "Nom d'utilisateur ou mot de passe invalide(s) !")
#         else:
#             messages.error(request, "Nom d'utilisateur ou mot de passe invalide(s) !")
#     else:
#         form = AuthenticationForm()

#     return render(request, "main/login.html", {"form": form})


# def signup_request(request):
#     if request.user.is_authenticated:
#         return redirect("main:homepage")

#     if request.method == "POST":
#         form = PublicUserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             username = form.cleaned_data.get('username')
#             messages.success(request, f"Compte créé avec succès pour {username}!")
#             # Automatically log in the user after signup

#             ActivityLogger.log_activity(
#                 user=user,
#                 activity_type=UserActivity.ACCOUNT_CREATED,
#                 request=request
#             )

#             print("User created:", user)

#             ActivityLogger.log_login(user, request)

#             login(request, user)
#             return redirect("main:homepage")
#         else:
#             messages.error(request, "Erreur lors de la création du compte. Veuillez vérifier les informations saisies.")
#     else:
#         form = PublicUserCreationForm()

#     return render(request, "main/signup.html", {"form": form})


# def list_students(request, group_id=None, app_id=None):
#     if request.user.is_authenticated:
#         user = request.user
#         if user.role == DefaultUser.TEACHER:
#             teacher = user
#             groups = AccessGroup.objects.exclude(name__exact=AccessGroup.FULL)
#             apps_to_template = []
#             current_group = None
#             current_app = None

#             data = dict()

#             try:
#                 group_id = int(group_id)
#             except:
#                 group_id = None

#             if group_id and group_id != AccessGroup.FULL:

#                 try:
#                     group = AccessGroup.objects.get(id=group_id)
#                     students = group.students.filter(role__exact=DefaultUser.STUDENT)
#                     apps = group.apps.all()
#                     current_group = group

#                 except AccessGroup.DoesNotExist:
#                     students = None
#                     apps = None

#                 apps_to_template = apps

#                 try:
#                     app_id = int(app_id)
#                 except:
#                     app_id = None

#                 if app_id:
#                     try:
#                         app = App.objects.get(id=app_id)
#                     except App.DoesNotExist:
#                         app = None

#                     if app:
#                         data[app.name] = []
#                         current_app = app
#                         for student in students:
#                             instance = None
#                             deployment_status = False
#                             try:
#                                 pod = Pod.objects.get(pod_user=student, app_name=app.name)
#                             except Pod.DoesNotExist:
#                                 pod = None
#                             #
#                             # if pod:
#                             #     try:
#                             #         instance = Instances.objects.get(pod=pod, instance_name=pod.pod_name)
#                             #     except Instances.DoesNotExist:
#                             #         instance = None
#                             # if pod and instance:
#                             #     deployment_status = True

#                             data[app.name].append({'info': student,
#                                                    **display_apps([app], student)[app.name]})

#             return render(request, 'main/list_students.html', {'data': data,
#                                                                'groups': groups,
#                                                                'apps': apps_to_template,
#                                                                'current_group': current_group,
#                                                                'current_app': current_app})

#     return render(request, 'main/display_apps.html')


# def continue_as_guest(request):
#     if request.user.is_authenticated:
#         return redirect('main:homepage')  # Prevent logged-in users from creating guest accounts

#     # Generate a unique guest username (e.g., "guest_12345")

#     guest_username = f"guest_{uuid.uuid4().hex[:6]}"

#     # Create a guest user
#     guest = DefaultUser.objects.create_user(
#         username=guest_username,
#         email=f"{guest_username}@example.com",  # Dummy email
#         password=None,  # No password (or generate a random one)
#         group=AccessGroup.objects.get(name=AccessGroup.GUEST),
#         role=DefaultUser.GUEST,
#         is_active=True,
#     )

#     # Log the guest in
#     ActivityLogger.log_activity(
#                 user=guest,
#                 activity_type=UserActivity.ACCOUNT_CREATED,
#                 request=request
#             )

#     login(request, guest)

#     ActivityLogger.log_login(guest, request)

#     return redirect('main:homepage')


# def sanitize_filename(filename):
#     """Sanitize filename to prevent path traversal and other attacks"""
#     if not filename:
#         return "unnamed_file"

#     # Use only the basename to strip any path components
#     clean_name = os.path.basename(filename)

#     # Remove or replace dangerous characters
#     dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
#     for char in dangerous_chars:
#         clean_name = clean_name.replace(char, '_')

#     # Ensure filename isn't empty after cleaning
#     if not clean_name or clean_name in ['.', '..']:
#         clean_name = "unnamed_file"

#     # Limit filename length
#     if len(clean_name) > 255:
#         name, ext = os.path.splitext(clean_name)
#         clean_name = name[:250] + ext

#     return clean_name


# def safe_base64_decode(encoded_path):
#     """Safely decode base64 with proper padding and error handling"""
#     if not encoded_path:
#         return ""

#     try:
#         # Add padding if necessary
#         pad = len(encoded_path) % 4
#         if pad:
#             encoded_path += "=" * (4 - pad)

#         decoded = base64.urlsafe_b64decode(encoded_path).decode('utf-8')
#         return decoded
#     except (binascii.Error, UnicodeDecodeError, ValueError):
#         raise SuspiciousOperation("Invalid path encoding")


# def validate_and_sanitize_path(path, user_base_path):
#     """Comprehensive path validation and sanitization"""
#     if not path:
#         return ""

#     # Normalize the path
#     path = os.path.normpath(path)

#     # Remove leading slash and strip whitespace
#     path = path.lstrip('/').strip()

#     # Block dangerous path components
#     path_parts = path.split('/')
#     for part in path_parts:
#         if part in ['.', '..', ''] or part.startswith('.'):
#             raise SuspiciousOperation("Invalid path component")

#     # Construct full path and resolve symlinks
#     if path:
#         full_path = os.path.join(user_base_path, path)
#     else:
#         full_path = user_base_path

#     real_path = os.path.realpath(full_path)
#     real_base = os.path.realpath(user_base_path)

#     # Ensure path is within allowed directory
#     if not real_path.startswith(real_base + os.sep) and real_path != real_base:
#         raise SuspiciousOperation("Path outside allowed directory")

#     return path


# def get_actual_storage_usage(user_path):
#     """Calculate actual storage usage by scanning filesystem"""
#     total_size = 0
#     try:
#         for root, dirs, files in os.walk(user_path):
#             for file in files:
#                 file_path = os.path.join(root, file)
#                 try:
#                     # Only count regular files, not symlinks
#                     if os.path.isfile(file_path) and not os.path.islink(file_path):
#                         total_size += os.path.getsize(file_path)
#                 except (OSError, IOError):
#                     continue  # Skip files we can't access
#     except (OSError, IOError):
#         pass

#     return total_size / (1024 * 1024)  # Convert to MB

# @never_cache
# @csrf_protect
# def file_explorer(request, path=None):
#     if not request.user.is_authenticated:
#         return redirect('main:landpage')

#     # Determine user path based on role
#     if request.user.role != DefaultUser.STUDENT and request.user.role != DefaultUser.GUEST:
#         user_path = '/READONLY/'
#         is_readonly = True
#     else:
#         user_path = f'/USERDATA/{request.user.username}/'
#         is_readonly = False

#     # Ensure user directory exists
#     os.makedirs(user_path, exist_ok=True)

#     try:
#         # Decode and validate path
#         if path:
#             decoded_path = safe_base64_decode(path)
#             validated_path = validate_and_sanitize_path(decoded_path, user_path)
#         else:
#             validated_path = ""

#         # Set up navigation
#         current_path = f'/{validated_path}' if validated_path else '/'

#         # Calculate parent path for navigation
#         if validated_path:
#             parent_parts = validated_path.split('/')[:-1]
#             parent_path = '/'.join(parent_parts) if parent_parts else ""
#             parent_path_encoded = base64.urlsafe_b64encode(parent_path.encode('utf-8')).decode() if parent_path else ""
#         else:
#             parent_path_encoded = ""

#     except SuspiciousOperation as e:
#         messages.error(request, "Invalid path access attempt.")
#         return redirect('main:file_explorer')

#     # Handle POST requests (upload/delete)
#     if request.method == 'POST':
#         action = request.POST.get('action')

#         # Handle file deletion (only for students)
#         if action == 'delete' and not is_readonly:
#             return handle_file_deletion(request, user_path, validated_path)

#         # Handle file upload
#         elif not is_readonly:
#             return handle_file_upload(request, user_path, validated_path)

#     # Get directory contents
#     try:
#         sub_files = get_sub_files_secure(user_path, validated_path)
#     except (OSError, IOError):
#         messages.error(request, "Unable to access directory.")
#         sub_files = {}

#     # Calculate storage usage for students
#     storage_percentage = 0
#     actual_usage = 0
#     if not is_readonly:
#         actual_usage = get_actual_storage_usage(user_path)
#         # Update user's stored usage to match reality
#         request.user.size_uploaded = actual_usage
#         request.user.save()
#         storage_percentage = min(100, (actual_usage / request.user.upload_limit) * 100)

#     form = UploadFileForm()

#     return render(request, 'main/file_explorer.html', {
#         'authenticated': True,
#         'data': sub_files,
#         'current_path': current_path,
#         'parent_path_encoded': parent_path_encoded,
#         'form': form,
#         'storage_percentage': storage_percentage,
#         'is_readonly': is_readonly,
#         'actual_usage': actual_usage
#     })


# def handle_file_deletion(request, user_path, current_path):
#     """Handle secure file deletion"""
#     file_path_encoded = request.POST.get('file_path')
#     if not file_path_encoded:
#         messages.error(request, "No file specified for deletion.")
#         return redirect_to_current_path(current_path)

#     try:
#         # Decode and validate file path
#         file_path_decoded = safe_base64_decode(file_path_encoded)
#         file_path_validated = validate_and_sanitize_path(file_path_decoded, user_path)

#         if not file_path_validated:
#             messages.error(request, "Invalid file path.")
#             return redirect_to_current_path(current_path)

#         full_file_path = os.path.join(user_path, file_path_validated)

#         # Security checks
#         if not os.path.exists(full_file_path):
#             messages.error(request, "File not found.")
#             return redirect_to_current_path(current_path)

#         if not os.path.isfile(full_file_path) or os.path.islink(full_file_path):
#             messages.error(request, "Can only delete regular files.")
#             return redirect_to_current_path(current_path)

#         # Get file size before deletion
#         try:
#             file_size_bytes = os.path.getsize(full_file_path)
#             file_size_mb = file_size_bytes / (1024 * 1024)
#         except OSError:
#             file_size_mb = 0

#         # Delete the file
#         os.remove(full_file_path)

#         # Update user's uploaded size
#         request.user.size_uploaded = max(0, request.user.size_uploaded - file_size_mb)
#         request.user.save()

#         filename = os.path.basename(file_path_validated)
#         messages.success(request, f"File '{escape(filename)}' deleted successfully. {file_size_mb:.2f}MB freed.")

#         ActivityLogger.log_file_activity(
#         user=request.user,
#         activity_type=UserActivity.FILE_DELETE,
#         filename=filename,
#         file_size=file_size_mb,
#         request=request
#         )

#     except (SuspiciousOperation, OSError, IOError) as e:
#         messages.error(request, "Error deleting file.")

#     return redirect_to_current_path(current_path)


# def handle_file_upload(request, user_path, current_path):
#     """Handle secure file upload"""
#     form = UploadFileForm(request.POST, request.FILES)

#     if not form.is_valid():
#         messages.error(request, "Please select a valid file.")
#         return redirect_to_current_path(current_path)

#     uploaded_file = request.FILES['file']
#     file_size_bytes = uploaded_file.size
#     file_size_mb = file_size_bytes / (1024 * 1024)

#     # File size validation (10MB limit)
#     if file_size_bytes > 10 * 1024 * 1024:
#         messages.error(request, "File size must not exceed 10MB.")
#         return redirect_to_current_path(current_path)

#     # User storage limit check
#     current_usage = get_actual_storage_usage(user_path)
#     if file_size_mb + current_usage > request.user.upload_limit:
#         available = request.user.upload_limit - current_usage
#         messages.error(request, f"Upload would exceed storage limit. Available: {available:.2f}MB")
#         return redirect_to_current_path(current_path)

#     # Sanitize filename
#     clean_filename = sanitize_filename(uploaded_file.name)

#     try:
#         # Construct safe save path
#         save_dir = os.path.join(user_path, current_path) if current_path else user_path
#         save_path = os.path.join(save_dir, clean_filename)

#         # Ensure we're not overwriting existing files
#         counter = 1
#         original_name, ext = os.path.splitext(clean_filename)
#         while os.path.exists(save_path):
#             clean_filename = f"{original_name}_{counter}{ext}"
#             save_path = os.path.join(save_dir, clean_filename)
#             counter += 1

#         # Save file securely
#         save_file_secure(save_path, uploaded_file)

#         # Update user's uploaded size
#         request.user.size_uploaded = current_usage + file_size_mb
#         request.user.save()

#         messages.success(request, f"File '{escape(clean_filename)}' uploaded successfully. {file_size_mb:.2f}MB used.")

#         ActivityLogger.log_file_activity(
#         user=request.user,
#         activity_type=UserActivity.FILE_UPLOAD,
#         filename=clean_filename,
#         file_size=file_size_mb,
#         request=request
#         )

#     except (IOError, OSError) as e:
#         messages.error(request, "Error saving file.")

#     return redirect_to_current_path(current_path)


# def redirect_to_current_path(current_path):
#     """Helper to redirect to current path safely"""
#     if current_path:
#         encoded_path = base64.urlsafe_b64encode(current_path.encode('utf-8')).decode()
#         return redirect('main:file_explorer', path=encoded_path)
#     else:
#         return redirect('main:file_explorer')

# @never_cache
# @csrf_protect
# def download_file(request, path):
#     if not request.user.is_authenticated:
#         raise Http404("Not authenticated")

#     try:
#         # Decode and validate path
#         decoded_path = safe_base64_decode(path)

#         # Determine user path
#         if request.user.role == DefaultUser.STUDENT or request.user.role == DefaultUser.GUEST:
#             user_path = f'/USERDATA/{request.user.username}/'
#         else:
#             user_path = '/READONLY/'

#         # Validate path
#         validated_path = validate_and_sanitize_path(decoded_path, user_path)

#         if not validated_path:
#             raise Http404("Invalid file path")

#         full_path = os.path.join(user_path, validated_path)

#         # Security checks
#         if not os.path.exists(full_path) or not os.path.isfile(full_path) or os.path.islink(full_path):
#             raise Http404("File not found")

#         # Get clean filename for download
#         filename = sanitize_filename(os.path.basename(validated_path))

#         # Use FileResponse for secure download
#         try:
#             response = FileResponse(
#                 open(full_path, 'rb'),
#                 as_attachment=True,
#                 filename=filename
#             )
#             ActivityLogger.log_file_activity(
#             user=request.user,
#             activity_type=UserActivity.FILE_DOWNLOAD,
#             filename=filename,
#             request=request
#             )
#             return response
#         except IOError:
#             raise Http404("Cannot access file")

#     except (SuspiciousOperation, UnicodeDecodeError, binascii.Error):
#         raise Http404("Invalid request")


# def get_sub_files_secure(user_path, path):
#     """Securely get directory contents with size information"""
#     sub_files = {}

#     try:
#         full_path = os.path.join(user_path, path) if path else user_path

#         if not os.path.exists(full_path) or not os.path.isdir(full_path):
#             return sub_files

#         for item in os.listdir(full_path):
#             # Skip hidden files and dangerous names
#             if item.startswith('.') or item in ['..', '.']:
#                 continue

#             item_path = os.path.join(full_path, item)

#             # Skip symlinks for security
#             if os.path.islink(item_path):
#                 continue

#             try:
#                 relative_path = os.path.join(path, item) if path else item
#                 encoded_path = base64.urlsafe_b64encode(relative_path.encode('utf-8')).decode()

#                 if os.path.isdir(item_path):
#                     sub_files[item] = {
#                         'path': encoded_path,
#                         'is_dir': True,
#                         'size': None,
#                         'escaped_name': escape(item)
#                     }
#                 elif os.path.isfile(item_path):
#                     try:
#                         file_size = os.path.getsize(item_path)
#                         sub_files[item] = {
#                             'path': encoded_path,
#                             'is_dir': False,
#                             'size': file_size,
#                             'escaped_name': escape(item)
#                         }
#                     except OSError:
#                         # Skip files we can't access
#                         continue
#             except (UnicodeEncodeError, OSError):
#                 # Skip problematic files
#                 continue

#     except (OSError, IOError):
#         pass  # Return empty dict if directory can't be accessed

#     return sub_files


# def save_file_secure(file_path, uploaded_file):
#     """Securely save uploaded file"""
#     # Ensure directory exists
#     directory = os.path.dirname(file_path)
#     os.makedirs(directory, exist_ok=True)

#     # Write file in chunks to handle large files efficiently and securely
#     with open(file_path, 'wb') as destination:
#         for chunk in uploaded_file.chunks():
#             destination.write(chunk)

#     # Set restrictive permissions (owner read/write only)
#     os.chmod(file_path, 0o600)


# # @background(schedule=timedelta(minutes=1))
# @autotask
# def stop_deployed_pod(pod_id, pod_name, app_name):
#     """Stop a deployed pod after a delay"""
#     # Logic to stop the pod
#     print("sleeping for 3 minutes before stopping the pod...")
#     sleep(60*3)  # Simulate a delay before stopping the pod
#     print(f"Stopping pod {pod_name} for app {app_name}...")
#     try:
#             config.load_kube_config()
#     except ConfigException:
#             config.load_incluster_config()

#     api_instance = client.CoreV1Api()
#     apps_instance = client.AppsV1Api()

#     # Delete ingress
#     delete_ingress(pod_name, app_name)
#     # Delete service
#     try:
#         deleted_service = api_instance.delete_namespaced_service(
#             namespace="apps",
#             name=app_name + "-service-" + pod_name
#         )
#     except ApiException as a:
#         print("delete service exception", a)
#     # Delete deployment
#     try:
#         deleted_deployment = apps_instance.delete_namespaced_deployment(
#             namespace="apps",
#             name=app_name + "-deployment-" + pod_name
#         )
#     except ApiException as a:
#         print("delete deployment exception", a)
#     # Delete instance record
#     try:
#         pod = Pod.objects.get(id=pod_id, app_name=app_name)
#         instance = Instances.objects.get(pod=pod, instance_name=pod_name)
#         instance.delete()

#         pod.is_deployed = False
#         pod.save()

#     except (Pod.DoesNotExist, Instances.DoesNotExist) as e:
#         print("instance already deleted", e)

#     print(f"Pod {pod_name} for app {app_name} has been stopped.")


# @never_cache
# def check_deployment_status(request):
#     """
#     Check the deployment status of applications for the authenticated user.
#     """

#     print("Checking deployment status for user:", request.user.username)
#     if request.user.is_authenticated:
#         print("Checking deployment status for user:", request.user.username)

#         if request.user.role == DefaultUser.TEACHER or request.user.role == DefaultUser.ADMIN:
#             apps = App.objects.all()
#             data = display_apps(apps, request.user)
#         else:
#             user = request.user
#             apps = user.group.apps.all()
#             data = display_apps(apps, user)

#         return JsonResponse(data)
#     return JsonResponse({})


# @never_cache
# def user_activities(request):
#     """View for admins to see user activities"""
#     if not request.user.is_authenticated or not request.user.is_superuser:
#         raise Http404("Page not found")

#     if not request.user.is_authenticated or request.user.role not in [DefaultUser.ADMIN]:
#         return redirect('main:landpage')


#     # Get filter parameters
#     filter_form = ActivityFilterForm(request.GET)
#     activities = UserActivity.objects.select_related('user').all()

#     # Apply filters
#     if filter_form.is_valid():
#         if filter_form.cleaned_data['user']:
#             activities = activities.filter(user=filter_form.cleaned_data['user'])

#         if filter_form.cleaned_data['activity_type']:
#             activities = activities.filter(activity_type=filter_form.cleaned_data['activity_type'])

#         if filter_form.cleaned_data['start_date']:
#             activities = activities.filter(timestamp__gte=filter_form.cleaned_data['start_date'])

#         if filter_form.cleaned_data['end_date']:
#             activities = activities.filter(timestamp__lte=filter_form.cleaned_data['end_date'])

#     # Search functionality
#     search_query = request.GET.get('search', '')
#     if search_query:
#         activities = activities.filter(
#             Q(user__username__icontains=search_query) |
#             Q(user__email__icontains=search_query) |
#             Q(ip_address__icontains=search_query)
#         )

#     # Pagination
#     paginator = Paginator(activities, 50)  # Show 50 activities per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     # Activity statistics
#     stats = {
#         'total_activities': activities.count(),
#         'today_activities': activities.filter(
#             timestamp__date=timezone.now().date()
#         ).count(),
#         'week_activities': activities.filter(
#             timestamp__gte=timezone.now() - timedelta(days=7)
#         ).count(),
#         'unique_users': activities.values('user').distinct().count(),
#     }

#     context = {
#         'page_obj': page_obj,
#         'filter_form': filter_form,
#         'search_query': search_query,
#         'stats': stats,
#     }

#     return render(request, 'main/user_activities.html', context)

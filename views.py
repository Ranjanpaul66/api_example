from django.shortcuts import render
from rest_framework.validators import ValidationError
from rest_framework.views import Response
from .serializers import *
import requests
from requests.exceptions import ConnectionError
from rest_framework.generics import ListCreateAPIView, CreateAPIView, ListAPIView
from django.db.models import Q
from rest_framework.renderers import JSONRenderer
from django.http import JsonResponse
from django.utils import timezone
from users.models import User
import hashlib
from django.db.utils import IntegrityError
import base64
import datetime
from django.utils import timezone
import dateutil.parser
from datetime import timedelta

from pubnub.pubnub import PubNub
from pubnub.pnconfiguration import PNConfiguration
from BOD.settings import subscribe_key, publish_key, channel_name, push_service

import pyfcm
from pyfcm import FCMNotification


# Create your views here.

class LoginView(CreateAPIView):

    def post(self, request, *args, **kwargs):
        if 'email' not in request.POST or request.POST['email'] is '':
            raise ValidationError({'message': 'Email is needed', 'status_code': '400'})

        if 'password' not in request.POST or request.POST['password'] is '':
            raise ValidationError({'message': 'Password is needed', 'status_code': '400'})

        if 'device_id' not in request.POST:
            raise ValidationError({'message': 'Device Id is needed', 'status_code': '400'})

        if 'fcm_key' not in request.POST:
            raise ValidationError({'message': 'FCM Key is needed', 'status_code': '400'})

        email = request.POST['email']
        user_password = request.POST['password']
        device_id = request.POST['device_id']
        fcm_key = request.POST['fcm_key']
        user_password = user_password.encode('utf-8')
        user_password = hashlib.sha256(user_password).hexdigest()

        base_url = request.build_absolute_uri('/')
        try:
            renter = User.objects.get(email=email)

            if renter.is_active != 1:
                return Response(
                    {'message': 'User is not active', 'status_code': '400', 'activation code': renter.is_active})
            else:
                print(user_password)
                if renter.password == user_password:
                    renter.device_id = device_id
                    renter.fcm_key = fcm_key
                    #-------------fcm checking---------
                    all_user = User.objects.all()
                    for user in all_user:
                        if device_id == user.device_id:
                            user.fcm_key = ''
                            user.save()
                    #---------------------------------
                    renter.save()
                    user_id = renter.id
                    user_type = renter.user_type
                    user_email = renter.email
                    user_name = renter.first_name + " " + renter.last_name
                    photo = base_url + 'assets/' + str(renter.photo)
                    phone = renter.phone
                    address = renter.address
                    designation = renter.designation
                    role = renter.role_id
                    activation_status = renter.is_active
                    device_id = renter.device_id
                    fcm_key = renter.fcm_key



                    return Response(
                        {'message': 'success', 'status_code': '200', 'user_id': user_id, 'user_type': user_type,
                         'name': user_name, 'photo': photo, 'phone': phone, 'address': address,
                         'designation': designation, 'role': role, 'activation_status': activation_status,
                         'email': user_email, 'device_id': device_id, 'fcm_key': fcm_key, })
                else:
                    return Response({'message': 'Failed' , 'status_code': '400', 'status':'Invalid Username or Password'})



        except User.DoesNotExist:
            return Response({'message': 'Failed', 'status_code': '400', 'status': 'User does not exist'})


class RegView(CreateAPIView):
    renderer_classes = (JSONRenderer,)

    def post(self, request, format=None):
        if 'first_name' not in request.POST or request.POST['first_name'] is '':
            raise ValidationError({'message': 'First Name is needed', 'status_code': '400'})

        if 'last_name' not in request.POST or request.POST['last_name'] is '':
            raise ValidationError({'message': 'Last Name is needed', 'status_code': '400'})

        if 'email' not in request.POST or request.POST['email'] is '':
            raise ValidationError({'message': 'Email is needed', 'status_code': '400'})

        if 'password' not in request.POST or request.POST['password'] is '':
            raise ValidationError({'message': 'Password is needed', 'status_code': '400'})

        if 'user_name' not in request.POST or request.POST['user_name'] is '':
            raise ValidationError({'message': 'User Name is needed', 'status_code': '400'})

        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        user_password = request.POST['password']
        user_name = request.POST['user_name']

        try:
            renter = User.objects.get(Q(email=email) | Q(user_name=user_name))
            return Response({'message': 'User is already existed', 'status_code': '400'})

        except User.DoesNotExist:
            create_user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=user_password,
                user_name=user_name,

            )
            response = {
                'first_name': str(first_name),
                'last_name': str(last_name),
                'email': str(email),
                'password': str(user_password),
                'user_name': str(user_name)

            }

            return JsonResponse({'message': 'success', 'status_code': '200', 'data': response})


class RoleWiseListView(CreateAPIView):
    serializer_class = UserSerializer
    renderer_classes = (JSONRenderer,)

    def post(self, request, format=None):
        if 'role_id' not in request.POST or request.POST['role_id'] is '':
            raise ValidationError({'message': 'Role ID is needed', 'status_code': '400'})

        role_id = request.POST['role_id']

        user_details = User.objects.filter(user_role=role_id)

        if not user_details:
            return Response({'message': 'User Does Not Exist', 'status_code': '400'})

        user_response = list()
        for user_details in user_details:
            user_response.append(
                {
                    'first_name': str(user_details.first_name),
                    'last_name': str(user_details.last_name),
                    'email': str(user_details.email),
                    'password': str(user_details.password),
                    'user_name': str(user_details.user_name),
                    'user_role': str(user_details.user_role),
                    'is_active': str(user_details.is_active)

                }

            )

        return JsonResponse({'message': 'success', 'status_code': '200', 'data': user_response})


class UserUpdateView(CreateAPIView):
    serializer_class = UserSerializer
    renderer_classes = (JSONRenderer,)

    def post(self, request, format=None):

        if 'user_id' not in request.POST or request.POST['user_id'] is '':
            raise ValidationError({'message': 'User ID is needed', 'status_code': '400'})

        if 'first_name' not in request.POST or request.POST['first_name'] is '':
            raise ValidationError({'message': 'First Name is needed', 'status_code': '400'})

        if 'last_name' not in request.POST or request.POST['last_name'] is '':
            raise ValidationError({'message': 'Last Name is needed', 'status_code': '400'})

        if 'email' not in request.POST or request.POST['email'] is '':
            raise ValidationError({'message': 'Email is needed', 'status_code': '400'})

        if 'password' not in request.POST or request.POST['password'] is '':
            raise ValidationError({'message': 'Password is needed', 'status_code': '400'})

        if 'is_active' not in request.POST or request.POST['is_active'] is '':
            raise ValidationError({'message': 'Activation ID is needed', 'status_code': '400'})

        if 'role_id' not in request.POST or request.POST['role_id'] is '':
            raise ValidationError({'message': 'Role ID is needed', 'status_code': '400'})

        if 'user_name' not in request.POST or request.POST['user_name'] is '':
            raise ValidationError({'message': 'User Name is needed', 'status_code': '400'})
        try:
            renter = User.objects.get(Q(email=request.POST['email']) | Q(user_name=request.POST['user_name']))
            if (renter.email == request.POST['email']):
                return Response({'message': 'Email already existed', 'status_code': '400'})
            if (renter.user_name == request.POST['user_name']):
                return Response({'message': 'User Name already existed', 'status_code': '400'})

        except:
            user_id = request.POST['user_id']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email = request.POST['email']
            user_password = request.POST['password']
            is_active = request.POST['is_active']
            # if is_active != 0 or is_active != 1:
            #     return Response({'message': 'Value must be 0 or 1 in Activation Code', 'status_code': '400', 'Activation Code': is_active })
            role_id = request.POST['role_id']
            # if (role_id != '1' or role_id != '2' or role_id!='3'):
            #     return Response({'message': 'Value must be 1 or 2 or 3 in Role ID', 'status_code': '400'})
            try:
                role_details = Role.objects.get(pk=role_id)
            except Role.DoesNotExist:
                return Response({'message': 'role Does Not Exist', 'status_code': '400'})

            user_name = request.POST['user_name']

            try:
                user_details = User.objects.get(pk=user_id)
                user_details.first_name = first_name
                user_details.last_name = last_name
                user_details.email = email
                user_details.password = user_password
                user_details.is_active = is_active
                user_details.user_role_id = role_id
                user_details.user_name = user_name
                user_details.save()

                response = {
                    'first_name': str(first_name),
                    'last_name': str(last_name),
                    'email': str(email),
                    'password': str(user_password),
                    'is_active': str(is_active),
                    'user_role': str(role_id),
                    'user_name': str(user_name)

                }
                return JsonResponse({'message': 'success', 'status_code': '200', 'data': response})

            except User.DoesNotExist:
                return Response({'message': 'User Does Not Exist', 'status_code': '400'})


class ProjectDetailsView(CreateAPIView):
    serializer_class = ProjectSerializer
    renderer_classes = (JSONRenderer,)

    def post(self, request, format=None):
        base_url = request.build_absolute_uri('/')

        if 'project_id' not in request.POST or request.POST['project_id'] is '':
            raise ValidationError({'message': 'Project ID is needed', 'status_code': '400'})

        project_id = request.POST['project_id']

        try:
            project_details = Project_Info.objects.get(pk=project_id)
        except Project_Info.DoesNotExist:
            return Response({'message': 'project Does Not Exist', 'status_code': '400'})

        assign_by_details = User.objects.get(pk=project_details.created_by_id)
        sponsored_by_details = User.objects.get(pk=project_details.sponsored_by_id)

        assigned_to = []
        project_manager = Project_Manager.objects.filter(project_id=project_details.id)
        for proect_mng in project_manager:
            # user_new=User.object.get(pk=proect_mng.assigned_to_id)
            assigned_to.append(proect_mng.assigned_to_id)

        assign_to_user_details = list()
        for assign_to_details in assigned_to:
            user_assign_to = User.objects.get(pk=assign_to_details)
            assign_to_user_details.append(
                {
                    'id': user_assign_to.id,
                    'name': user_assign_to.first_name + " " + user_assign_to.last_name,
                    'designation': user_assign_to.designation,
                    'photo': base_url + 'assets/' + str(user_assign_to.photo),
                }
            )

        director_list = User.objects.filter(user_type=1)
        director_number = len(director_list)

        project_status = Project_Status.objects.filter(project_id=project_id)
        status_by_details = []
        if (len(project_status) == director_number-1):
            status_list = []
            for status in project_status:
                status_list.append(status.status)
            if status_list.count(1) == director_number-1:
                print(status_list.count(1))
                project_details.status = 1
            else:
                project_details.status = 2

            project_details.save()
        if (len(project_status) > 0):
            edit_status = 1
            for people in project_status:
                people_info = User.objects.get(pk=people.user_id)
                status_by_details.append(people_info.id
                    # {
                    #     'user_id': people_info.id,
                    #     'name': people_info.first_name + " " + people_info.last_name,
                    #     'photo': base_url + 'assets/' + str(people_info.photo),
                    # }
                )

        else:
            edit_status = 0

        return JsonResponse({'message': 'success', 'status_code': '200', 'title': str(project_details.title),
                             'code': str(project_details.code),
                             'status': project_details.status,
                             'team_size': str(project_details.team_size),
                             'duration': str(project_details.duration),
                             'response_day': str(project_details.response_day),
                             'budget': str(project_details.budget),
                             'revenue_plan': str(project_details.revenue_plan),
                             'target_revenue': str(project_details.target_revenue),
                             'additional_cost': str(project_details.additional_cost),
                             'type': str(project_details.type),
                             'project_type_id': project_details.type_id,
                             'details': str(project_details.details),
                             'assigned_by_id': assign_by_details.id,
                             'assigned_by_name': assign_by_details.first_name + " " + assign_by_details.last_name,
                             'assigned_by_designation': assign_by_details.designation,
                             'assigned_by_photo': base_url + 'assets/' + str(assign_by_details.photo),
                             'sponsored_by_id': sponsored_by_details.id,
                             'sponsored_by_name': sponsored_by_details.first_name + " " + sponsored_by_details.last_name,
                             'sponsored_by_contact': sponsored_by_details.phone,
                             'sponsored_by_email': sponsored_by_details.email,
                             'sponsored_by_designation': sponsored_by_details.designation,
                             'sponsored_by_photo': base_url + 'assets/' + str(sponsored_by_details.photo),
                             'assigned_to': assign_to_user_details,
                             'edit_status': edit_status,
                             'status_by': status_by_details,
                             'approve_count':len(project_status),

                             })

class ProjectListView(CreateAPIView):
    serializer_class = ProjectSerializer
    renderer_classes = (JSONRenderer,)

    def post(self, request, format=None):
        base_url = request.build_absolute_uri('/')

        director_list = User.objects.filter(user_type=1)
        director_number = len(director_list)

        project_lists = Project_Info.objects.all().order_by('-created_at')

        project_response = list()
        for project_list in project_lists:
            user_assign_by = User.objects.get(pk=project_list.created_by_id)
            user_sponsored_by = User.objects.get(pk=project_list.sponsored_by_id)
            assigned_to = []
            project_manager = Project_Manager.objects.filter(project_id=project_list.id)
            for proect_mng in project_manager:
                assigned_to.append(proect_mng.assigned_to_id)

            assign_to_user_details = list()
            for assign_to_details in assigned_to:
                user_assign_to = User.objects.get(pk=assign_to_details)
                assign_to_user_details.append(
                    {
                        'id': user_assign_to.id,
                        'name': user_assign_to.first_name + " " + user_assign_to.last_name,
                        'designation': user_assign_to.designation,
                        'photo': base_url + 'assets/' + str(user_assign_to.photo),
                    }
                )
            project_id = project_list.id
            project_status = Project_Status.objects.filter(project_id=project_id)
            status_by_details = list()

            if (len(project_status) == director_number-1):
                project_info_status = Project_Info.objects.get(pk=project_id)
                status_list = []
                for status in project_status:
                    status_list.append(status.status)
                if status_list.count(1) == director_number-1:
                    project_info_status.status = 1
                else:
                    project_info_status.status = 2
                project_info_status.save()

            if (len(project_status) > 0):
                edit_status = 1
                for people in project_status:
                    people_info = User.objects.get(pk=people.user_id)
                    status_by_details.append(
                        {
                            'user_id': people_info.id,
                            'name': people_info.first_name + " " + people_info.last_name,
                        }
                    )

            else:
                edit_status = 0

            modified_project_status = Project_Info.objects.get(pk=project_id)

            project_response.append(
                {
                    'id': project_list.id,
                    'title': project_list.title,
                    'code': project_list.code,

                    'status': modified_project_status.status,
                    'details': project_list.details,
                    'assigned_by_id': user_assign_by.id,
                    'assigned_by_name': user_assign_by.first_name + " " + user_assign_by.last_name,
                    'assigned_by_designation': user_assign_by.designation,
                    'assigned_by_photo': base_url + 'assets/' + str(user_assign_by.photo),
                    'assigned_to': assign_to_user_details,
                    'sponsored_by_id': user_sponsored_by.id,
                    'sponsored_by_name': user_sponsored_by.first_name + " " + user_sponsored_by.last_name,
                    'sponsored_by_designation': user_sponsored_by.designation,
                    'sponsored_by_photo': base_url + 'assets/' + str(user_sponsored_by.photo),
                    'edit_status': edit_status,
                    'status_by': status_by_details,
                    'approve_count': len(project_status),

                }

            )

        return JsonResponse({'message': 'success', 'status_code': '200', 'data': project_response})


class AddProjectView(CreateAPIView):
    serializer_class = ProjectManagerSerializer, ProjectManagerSerializer

    def post(self, request, format=None):

        if 'title' not in request.POST or request.POST['title'] is '':
            raise ValidationError({'message': 'Project Title is needed', 'status_code': '400'})
        if 'code' not in request.POST or request.POST['code'] is '':
            raise ValidationError({'message': 'Code is needed', 'status_code': '400'})
        if 'details' not in request.POST or request.POST['details'] is '':
            raise ValidationError({'message': 'Details is needed', 'status_code': '400'})
        if 'team_size' not in request.POST or request.POST['team_size'] is '':
            raise ValidationError({'message': 'Team Size is needed', 'status_code': '400'})
        if 'duration' not in request.POST or request.POST['duration'] is '':
            raise ValidationError({'message': 'Duration is needed', 'status_code': '400'})
        if 'response_day' not in request.POST or request.POST['response_day'] is '':
            raise ValidationError({'message': 'Response Day is needed', 'status_code': '400'})
        if 'budget' not in request.POST or request.POST['budget'] is '':
            raise ValidationError({'message': 'Budget is needed', 'status_code': '400'})
        if 'revenue_plan' not in request.POST or request.POST['revenue_plan'] is '':
            raise ValidationError({'message': 'Revenue Plan is needed', 'status_code': '400'})
        if 'target_revenue' not in request.POST or request.POST['target_revenue'] is '':
            raise ValidationError({'message': 'Target Revenue is needed', 'status_code': '400'})
        if 'additional_cost' not in request.POST or request.POST['additional_cost'] is '':
            raise ValidationError({'message': 'Additional Cost is needed', 'status_code': '400'})
        if 'type' not in request.POST or request.POST['type'] is '':
            raise ValidationError({'message': 'Type is needed', 'status_code': '400'})
        if 'assigned_to' not in request.POST or request.POST['assigned_to'] is '':
            raise ValidationError({'message': 'Assigned To is needed', 'status_code': '400'})
        if 'assigned_by' not in request.POST or request.POST['assigned_by'] is '':
            raise ValidationError({'message': 'Assigned By is needed', 'status_code': '400'})
        if 'sponsored_by' not in request.POST or request.POST['sponsored_by'] is '':
            raise ValidationError({'message': 'Sponsored By is needed', 'status_code': '400'})

        title = request.POST['title']
        code = request.POST['code']  # unique
        print(code)
        try:
            project_code = Project_Info.objects.get(code=code)
            return Response({'message': 'Project Code is already existed', 'status_code': '400'})

        except Project_Info.DoesNotExist:
            details = request.POST['details']
            team_size = request.POST['team_size']
            duration = request.POST['duration']
            response_day = request.POST['response_day']
            budget = request.POST['budget']
            revenue_plan = request.POST['revenue_plan']
            target_revenue = request.POST['target_revenue']
            additional_cost = request.POST['additional_cost']
            type = request.POST['type']  # foreign
            try:
                project_type = Project_Type.objects.get(pk=type)
            except Project_Type.DoesNotExist:
                return Response({'message': 'project Type Does Not Exist', 'status_code': '400'})
            assigned_by = request.POST['assigned_by']
            try:
                project_assigned_by = User.objects.get(pk=assigned_by)
            except User.DoesNotExist:
                return Response({'message': 'Assigned By Does Not Exist', 'status_code': '400'})

            sponsored_by = request.POST['sponsored_by']
            try:
                project_sponsored_by = User.objects.get(pk=sponsored_by)
            except User.DoesNotExist:
                return Response({'message': 'Sponsored By Does Not Exist', 'status_code': '400'})

            create_project_info = Project_Info.objects.create(

                title=title,
                code=code,
                details=details,
                team_size=team_size,
                duration=duration,
                response_day=response_day,
                budget=budget,
                revenue_plan=revenue_plan,
                target_revenue=target_revenue,
                additional_cost=additional_cost,
                type=project_type,
                created_at=timezone.now(),

                modified_at=timezone.now(),
                created_by=project_assigned_by,
                modified_by=project_assigned_by,
                sponsored_by=project_sponsored_by
            )
            assigned_to = request.POST['assigned_to']  # foreign

            assigned_to = assigned_to.split(",")
            registration_ids = []
            user_ids = []
            for person in assigned_to:
                try:
                    project_assigned_to = User.objects.get(pk=person)
                    create_project_manager = Project_Manager.objects.create(
                        project_id=create_project_info.id,
                        assigned_by=project_assigned_by,
                        assigned_to=project_assigned_to,
                        created_at=timezone.now(),
                        modified_at=timezone.now(),
                        created_by=project_assigned_by,
                        modified_by=project_assigned_by

                    )
                    if project_assigned_to.id!=project_assigned_by.id:
                        registration_ids.append(project_assigned_to.fcm_key)
                        user_ids.append(project_assigned_to.id)
                        create_push_log = Push_Log.objects.create(
                            project_id=create_project_info.id,
                            user_id=project_assigned_to.id,
                            sponsored_by_id=project_sponsored_by.id,
                            type=1,
                            status=1

                        )
                    #print(person)



                except User.DoesNotExist:
                    return Response({'message': 'Assignee ' + person + ' Does Not Exist', 'status_code': '400'})

            base_url = request.build_absolute_uri('/')
            data_message = {
                "payload":
                    {
                            "project_id": create_project_info.id,
                            "android": {
                                "title": project_sponsored_by.first_name + ' ' + project_sponsored_by.last_name,
                                "alert": str('New: '+ str(create_project_info.title)),
                                "icon": project_sponsored_by.username,
                                "badge": "1",
                                "vibrate": True

                            }

                    }
            }
            message_title = "Project Created"
            message_body = "Update Push Log"

            director_list = User.objects.filter(user_type=1)
            for director in director_list:
                print(project_assigned_by.id)
                if (director.id != project_assigned_by.id):
                    #print(director.id)
                    registration_ids.append(director.fcm_key)
                    user_ids.append(director.id)
                    if director.id==project_sponsored_by.id:
                        create_push_log = Push_Log.objects.create(
                            project_id=create_project_info.id,
                            user_id=director.id,
                            sponsored_by_id=project_sponsored_by.id,
                            type=1,
                            status = 1

                        )
                    else:
                        create_push_log = Push_Log.objects.create(
                            project_id=create_project_info.id,
                            user_id=director.id,
                            sponsored_by_id=project_sponsored_by.id,
                            type=1,

                        )


            result = push_service.multiple_devices_data_message(registration_ids=registration_ids,data_message=data_message)
            success_positions = []
            if result['success'] > 0:
                for error, i in zip(result['results'], range(0, len(result['results']))):
                    try:
                        if error['error'] == 'InvalidRegistration':
                            pass
                    except KeyError:
                        success_positions.append(i)

            for success_position in success_positions:
                user = user_ids[success_position]
                success_update_in_push_log = Push_Log.objects.get(Q(user_id=user),Q(project_id=create_project_info.id))
                success_update_in_push_log.message_sending_status = 1
                success_update_in_push_log.created_at=timezone.now()
                success_update_in_push_log.save()
            return JsonResponse({'message': 'success', 'status_code': '200'})

class ProjectTypeView(CreateAPIView):
    serializer_class = ProjectTypeSerializer

    def post(self, request, format=None):

        try:
            all_project_type = Project_Type.objects.all()
        except Project_Type.DoesNotExist:
            return Response({'message': ' No Project Exist', 'status_code': '400'})

        project_type = list()
        for project_type_info in all_project_type:
            project_type.append(
                {
                    'id': str(project_type_info.id),
                    'title': str(project_type_info.name),
                }
            )

        return JsonResponse({'project_type': project_type, 'message': 'success', 'status_code': '200'})


class UserListView(CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, format=None):
        try:
            all_user = User.objects.all()
        except User.DoesNotExist:
            return Response({'message': 'No User Exist', 'status_code': '400'})

        director_list = list()
        manager_list = list()
        base_url = request.build_absolute_uri('/')
        for user in all_user:
            if user.user_type == 1:
                director_list.append(
                    {
                        'id': user.id,
                        'user_type': user.user_type,
                        'designation': user.designation,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'username': user.username,
                        'email': user.email,
                        'phone_number': user.phone,
                        'address': user.address,
                        'status': user.is_active,
                        'photo': base_url + 'assets/' + str(user.photo),

                    })
            if user.user_type == 2:
                manager_list.append(
                    {
                        'id': user.id,
                        'user_type': user.user_type,
                        'designation': user.designation,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'username': user.username,
                        'email': user.email,
                        'phone_number': user.phone,
                        'address': user.address,
                        'status': user.is_active,
                        'photo': base_url + 'assets/' + str(user.photo),

                    }

                )
        return JsonResponse(
            {'director_list': director_list, 'manager_list': manager_list, 'message': 'success', 'status_code': '200'})


class UserProjectListView(CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, format=None):
        if 'user_id' not in request.POST or request.POST['user_id'] is '':
            raise ValidationError({'message': 'User ID is needed', 'status_code': '400'})

        user_id = request.POST['user_id']

        try:
            user_all_project = Project_Info.objects.filter(created_by_id=user_id).order_by('-created_at')
        except User.DoesNotExist:
            return Response({'message': 'No Project Exist For The User', 'status_code': '400'})

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'message': 'User does not exist', 'status_code': '400'})

        project_list = list()
        base_url = request.build_absolute_uri('/')

        for project_info in user_all_project:

            assigned_to = []
            project_manager = Project_Manager.objects.filter(project_id=project_info.id)
            project_sponsored_by = User.objects.get(pk=project_info.sponsored_by_id)
            for proect_mng in project_manager:
                # user_new=User.object.get(pk=proect_mng.assigned_to_id)
                assigned_to.append(proect_mng.assigned_to_id)

            assign_to_user_details = list()
            for assign_to_details in assigned_to:
                user_assign_to = User.objects.get(pk=assign_to_details)
                assign_to_user_details.append(
                    {
                        'id': user_assign_to.id,
                        'name': user_assign_to.first_name + " " + user_assign_to.last_name,
                        'designation': user_assign_to.designation,
                        'photo': base_url + 'assets/' + str(user_assign_to.photo),
                    }
                )
            director_list = User.objects.filter(user_type=1)
            director_number = len(director_list)
            project_status = Project_Status.objects.filter(project_id=project_info.id)
            status_by_details = list()

            if (len(project_status) == director_number-1):

                status_list = []
                for status in project_status:
                    status_list.append(status.status)
                if status_list.count(1) == director_number-1:
                    project_info.status = 1
                else:
                    project_info.status = 2
                project_info.save()

            if (len(project_status) > 0):
                edit_status = 1
                for people in project_status:
                    people_info = User.objects.get(pk=people.user_id)
                    status_by_details.append(
                        {
                            'user_id': people_info.id,
                            'name': people_info.first_name + " " + people_info.last_name,
                        }
                    )

            else:
                edit_status = 0

            project_list.append(
                {
                    'user_name': user.first_name,
                    'project_id': project_info.id,

                    'project_title': project_info.title,
                    'status': project_info.status,
                    'description': project_info.details,
                    'assigned_by_id': project_info.created_by_id,
                    'assigned_by_name': user.first_name + " " + user.last_name,
                    'assigned_by_designation': user.designation,
                    'assigned_by_photo': base_url + 'assets/' + str(user.photo),
                    'sponsored_by_id': project_info.sponsored_by_id,
                    'sponsored_by_name': project_sponsored_by.first_name + " " + project_sponsored_by.last_name,
                    'sponsored_by_designation': project_sponsored_by.designation,
                    'sponsored_by_photo': base_url + 'assets/' + str(project_sponsored_by.photo),
                    'assigned_to': assign_to_user_details,
                    'edit_status': edit_status,
                    'status_by': status_by_details,
                    'approve_count': len(project_status),

                }

            )
        return JsonResponse({'project_list': project_list, 'message': 'success', 'status_code': '200'})

class AddProjectStatusView(CreateAPIView):

    def post(self, request, format=None):

        if 'project_id' not in request.POST or request.POST['project_id'] is '':
            raise ValidationError({'message': 'Project ID is needed', 'status_code': '400'})
        if 'status' not in request.POST or request.POST['status'] is '':
            raise ValidationError({'message': 'Status is needed', 'status_code': '400'})
        if 'user_id' not in request.POST or request.POST['user_id'] is '':
            raise ValidationError({'message': 'User Id is needed', 'status_code': '400'})
        if 'comment' not in request.POST:
            raise ValidationError({'message': 'Comment is needed', 'status_code': '400'})

        project_id = request.POST['project_id']
        try:
            project = Project_Info.objects.get(pk=project_id)
        except Project_Info.DoesNotExist:
            return Response({'message': 'Project Does Not Exist', 'status_code': '400'})
        status = request.POST['status']

        user_id = request.POST['user_id']
        comment = request.POST['comment']
        try:
            user = User.objects.get(pk=user_id)
            project_sponsored_by = User.objects.get(pk = project.sponsored_by_id)
        except User.DoesNotExist:
            return Response({'message': 'User Does Not Exist', 'status_code': '400'})

        try:
            existed_status = Project_Status.objects.get(Q(project_id=project_id),Q(user_id=user_id))
            return Response({'message': 'You have already given status', 'status_code': '400'})

        except Project_Status.DoesNotExist:


            create_project_info = Project_Status.objects.create(
                project=project,
                status=status,
                comment=comment,
                user=user,
                created_at=timezone.now(),
                modified_at=timezone.now(),
                created_by=user,
                modified_by=user

            )
            #-----------------------

            if int(status) == 1:
                given_status = 'approved by '
            else:
                given_status = 'rejected by '
            data_message = {
                "payload":
                    {
                        "project_id": project.id,
                        "android": {
                            "title": project_sponsored_by.first_name + ' ' + project_sponsored_by.last_name,
                            "alert": project.title + ', ' + given_status + user.first_name+' '+user.last_name,
                            "icon": project_sponsored_by.username,
                            "badge": "1",
                            "vibrate": True

                        }

                    }
            }
            director_list = User.objects.filter(user_type=1)
            registration_ids = []
            for director in director_list:
                if director.id != int(user_id):
                    registration_ids.append(director.fcm_key)

            #-----------------------
            if project.created_by_id!=user_id:
                try:
                    push_log = Push_Log.objects.get(Q(project_id=project_id), Q(user_id=user_id))
                    push_log.status = status
                    push_log.save()
                    result = push_service.multiple_devices_data_message(registration_ids=registration_ids,
                                                                        data_message=data_message)
                    print(result)
                except Push_Log.DoesNotExist:
                    raise ValidationError({'message': 'Push Log does not exist', 'status_code': '400'})

            return JsonResponse({'message': 'success', 'status_code': '200'})


class ProjectUpdateView(CreateAPIView):
    serializer_class = ProjectSerializer

    def post(self, request, *args, **kwargs):
        if 'project_id' not in request.POST or request.POST['project_id'] is '':
            raise ValidationError({'message': 'Project ID is needed', 'status_code': '400'})

        project_id = request.POST['project_id']
        try:
            project_obj = Project_Info.objects.get(id=project_id)
        except Project_Info.DoesNotExist:
            raise ValidationError({'message': 'Project does not exist', 'status_code': '400'})

        if 'title' not in request.POST or request.POST['title'] is '':
            raise ValidationError({'message': 'Project Title is needed', 'status_code': '400'})
        if 'code' not in request.POST or request.POST['code'] is '':
            raise ValidationError({'message': 'Code is needed', 'status_code': '400'})
        if 'details' not in request.POST or request.POST['details'] is '':
            raise ValidationError({'message': 'Details is needed', 'status_code': '400'})
        if 'team_size' not in request.POST or request.POST['team_size'] is '':
            raise ValidationError({'message': 'Team Size is needed', 'status_code': '400'})
        if 'duration' not in request.POST or request.POST['duration'] is '':
            raise ValidationError({'message': 'Duration is needed', 'status_code': '400'})
        if 'response_day' not in request.POST or request.POST['response_day'] is '':
            raise ValidationError({'message': 'Response Day is needed', 'status_code': '400'})
        if 'budget' not in request.POST or request.POST['budget'] is '':
            raise ValidationError({'message': 'budget is needed', 'status_code': '400'})
        if 'revenue_plan' not in request.POST or request.POST['revenue_plan'] is '':
            raise ValidationError({'message': 'Revenue Plan is needed', 'status_code': '400'})
        if 'target_revenue' not in request.POST or request.POST['target_revenue'] is '':
            raise ValidationError({'message': 'Target Revenue is needed', 'status_code': '400'})
        if 'additional_cost' not in request.POST or request.POST['additional_cost'] is '':
            raise ValidationError({'message': 'Additional Cost is needed', 'status_code': '400'})
        if 'type' not in request.POST or request.POST['type'] is '':
            raise ValidationError({'message': 'Type is needed', 'status_code': '400'})
        if 'assigned_by' not in request.POST or request.POST["assigned_by"] is '':
            raise ValidationError({'message': "assigned_by is needed ", 'status_code': '400'})

        if 'assigned_to' not in request.POST or request.POST["assigned_to"] is '':
            raise ValidationError({'message': "assigned_to is needed ", 'status_code': '400'})
        else:
            project_manager_obj = Project_Manager.objects.filter(project_id=project_id).delete()
        title = request.POST['title']
        code = request.POST['code']
        try:
            project_code = Project_Info.objects.get(Q(code=code), ~Q(pk=project_id))
            return Response({'message': 'Project Code is already existed', 'status_code': '400'})

        except Project_Info.DoesNotExist:
            details = request.POST['details']
            team_size = request.POST['team_size']
            duration = request.POST['duration']
            response_day = request.POST['response_day']
            budget = request.POST['budget']
            revenue_plan = request.POST['revenue_plan']
            target_revenue = request.POST['target_revenue']
            additional_cost = request.POST['additional_cost']
            project_type = request.POST['type']
            try:
                project_type = Project_Type.objects.get(pk=project_type)
            except Project_Type.DoesNotExist:
                return Response({'message': 'project Type Does Not Exist', 'status_code': '400'})
            assigned_by = request.POST['assigned_by']
            try:
                project_assigned_by = User.objects.get(pk=assigned_by)
            except User.DoesNotExist:
                return Response({'message': 'Assigned By Does Not Exist', 'status_code': '400'})

            try:

                project_obj.title = title
                project_obj.code = code
                project_obj.details = details
                project_obj.team_size = team_size
                project_obj.duration = duration
                project_obj.response_day = response_day
                project_obj.budget = budget
                project_obj.revenue_plan = revenue_plan
                project_obj.target_revenue = target_revenue
                project_obj.additional_cost = additional_cost
                project_obj.type_id = project_type
                project_obj.modified_at = timezone.now()

                project_obj.save()

            except IntegrityError as e:
                raise ValidationError({'message': e.__str__(), 'status_code': '400'})
            assigned_to = request.POST['assigned_to']  # foreign
            assigned_to = assigned_to.split(",")

            for person in assigned_to:
                try:
                    project_assigned_to = User.objects.get(pk=person)
                    create_project_manager = Project_Manager.objects.create(
                        project_id=project_obj.id,
                        assigned_by_id=project_assigned_by.id,
                        assigned_to_id=project_assigned_to.id,
                        #created_at=timezone.now(),
                        modified_at=timezone.now(),
                        created_by_id=project_assigned_by.id,
                        modified_by_id=project_assigned_by.id

                    )
                except User.DoesNotExist:
                    return Response({'message': 'Assignee ' + person + ' Does Not Exist', 'status_code': '400'})

            base_url = request.build_absolute_uri('/')
            project_sponsored_by = User.objects.get(id=project_obj.sponsored_by_id)
            data_message = {
                "payload":
                    {
                        "project_id": project_obj.id,
                        "android": {
                            "title": project_sponsored_by.first_name + ' ' + project_sponsored_by.last_name,
                            "alert": str('Update: '+str(project_obj.title)),
                            "icon": project_sponsored_by.username,
                            "badge": "1",
                            "vibrate": True

                        }

                    }
            }
            message_title = "Project Updated"
            message_body = "Update Push Log"
            registration_ids = []

            director_list = User.objects.filter(user_type=1)
            for director in director_list:
                if (director.id != project_sponsored_by.id):
                    print(director.id)
                    registration_ids.append(director.fcm_key)
                    # update_push_log = Push_Log.objects.get(Q(project_id=project_obj.id),Q(user_id=director.id))
                    # update_push_log.type=2
                    # update_push_log.save()
                    # create_push_log = Push_Log.objects.create(
                    #     project_id=project_obj.id,
                    #     user_id=director.id,
                    #     sponsored_by_id=project_sponsored_by.id,
                    #     type=2
                    #
                    # )

            result = push_service.multiple_devices_data_message(registration_ids=registration_ids, data_message=data_message)
            #print(result)
            return JsonResponse({'message': 'success', 'status_code': '200'})


class Base64View(CreateAPIView):
    def post(self, request, *args, **kwargs):
        if 'name' not in request.POST or request.POST['name'] is '':
            raise ValidationError({'message': 'Name is needed', 'status_code': '400'})
        if 'image' not in request.POST or request.POST['image'] is '':
            raise ValidationError({'message': 'Image is needed', 'status_code': '400'})

        name = request.POST['name']
        image = request.POST['image']
        # a= base64.e
        print(image)
        fh = open('taimur.jpg', "wb")
        fh.write(base64.decodebytes(image.encode()))
        fh.close()

        return JsonResponse({'message': 'success', 'status_code': '200'})


class ResetPassword(CreateAPIView):

    def post(self, request, *args, **kwargs):

        if 'email' not in request.POST or request.POST['email'] is '':
            raise ValidationError({'message': 'Email is needed', 'status_code': '400'})
        if 'old_password' not in request.POST or request.POST['old_password'] is '':
            raise ValidationError({'message': 'Old password is needed', 'status_code': '400'})
        if 'new_password' not in request.POST or request.POST['new_password'] is '':
            raise ValidationError({'message': 'New password is needed', 'status_code': '400'})

        email = request.POST['email']
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']

        try:
            user_info = User.objects.get(email=email)

            old_password = old_password.encode('utf-8')
            old_password = hashlib.sha256(old_password).hexdigest()

            if user_info.password == old_password:
                new_password = new_password.encode('utf-8')
                new_password = hashlib.sha256(new_password).hexdigest()
                user_info.password = new_password
                user_info.save()
                return Response({'message': 'success', 'status_code': '200'})
            else:
                return Response({'message': 'Wrong password', 'status_code': '400'})

        except User.DoesNotExist:
            return Response({'message': 'User Invalid', 'status_code': '400'})


class PushLogUpdateView(CreateAPIView):
    def post(self, request, *args, **kwargs):
        if 'project_id' not in request.POST or request.POST['project_id'] is '':
            raise ValidationError({'message': 'Project Id is needed', 'status_code': '400'})
        if 'status' not in request.POST or request.POST['status'] is '':
            raise ValidationError({'message': 'Status is needed', 'status_code': '400'})
        if 'user_id' not in request.POST or request.POST['user_id'] is '':
            raise ValidationError({'message': 'User Id is needed', 'status_code': '400'})

        project_id = request.POST['project_id']
        try:
            project = Project_Info.objects.get(id=project_id)
        except Project_Info.DoesNotExist:
            raise ValidationError({'message': 'Project does not exist', 'status_code': '400'})
        status = request.POST['status']
        user_id = request.POST['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError({'message': 'User does not exist', 'status_code': '400'})

        try:
            push_log = Push_Log.objects.get(Q(project_id=project_id), Q(user_id=user_id))

            push_log.status = status
            push_log.save()
        except Push_Log.DoesNotExist:
            raise ValidationError({'message': 'Push Log does not exist', 'status_code': '400'})

        return JsonResponse({'message': 'success', 'status_code': '200'})


def PushNotificationBySchedulerView(request):
    push_log_status_0 = Push_Log.objects.filter(status=0)
    unique_project = []
    # pnconfig = PNConfiguration()
    # pnconfig.subscribe_key = subscribe_key
    # pnconfig.publish_key = publish_key
    # pubnub = PubNub(pnconfig)

    base_url = request.build_absolute_uri('/')

    message_body = "Update Push Log"


    for push_log in push_log_status_0:
        if push_log.project_id not in unique_project:
            unique_project.append(push_log.project_id)

    for project in unique_project:



        project_info = Project_Info.objects.get(id=project)
        sponsored_by_details = User.objects.get(id=project_info.sponsored_by_id)

        response_day=project_info.response_day
        start_date= str(project_info.created_at)
        start_date = start_date.split('+')
        start_date = dateutil.parser.parse(start_date[0])
        end_date = datetime.datetime.now()
        duration = end_date - start_date

        date_count_check = Push_Log.objects.filter(project_id=project)

        date_status = date_count_check[0].day_count_for_notification

        data_message = {
            "payload":
                {
                    "project_id": project_info.id,
                    "android": {
                        "title": sponsored_by_details.first_name + ' ' + sponsored_by_details.last_name,
                        "alert": project_info.title,
                        "icon": sponsored_by_details.username,
                        "badge": "1",
                        "vibrate": True

                    }

                }
        }

        if duration.days <= int(response_day):
        #if duration.days > date_status and duration.days<=int(response_day):
            for every_director in date_count_check:
                every_director.day_count_for_notification=every_director.day_count_for_notification+1
                every_director.save()

            project_assign_push = Push_Log.objects.filter(Q(project_id=project_info.id), Q(status=0))
            if len(project_assign_push)>0:
                registration_ids = []
                user_ids = []
                message_title = "Project Created"
                for user in project_assign_push:
                    director = User.objects.get(pk=user.user_id)
                    registration_ids.append(director.fcm_key)
                    user_ids.append(director.id)

                result = push_service.multiple_devices_data_message(registration_ids=registration_ids,data_message=data_message)
                # success_positions = []
                # if result['success'] > 0:
                #     for error, i in zip(result['results'], range(0, len(result['results']))):
                #         try:
                #             if error['error'] == 'InvalidRegistration':
                #                 pass
                #         except KeyError:
                #             success_positions.append(i)
                #
                # for success_position in success_positions:
                #     user = user_ids[success_position]
                #
                #     success_update_in_push_log = Push_Log.objects.get(Q(user_id=user),
                #                                                       Q(project_id=project_info.id))
                #     success_update_in_push_log.message_sending_status = 1
                #     success_update_in_push_log.modified_at = timezone.now()
                #     success_update_in_push_log.save()

                print(result)

            # project_update_push = Push_Log.objects.filter(Q(type=2), Q(project_id=project_info.id))
            # if len(project_update_push)>0:
            #     registration_ids = []
            #     message_title = "Project Updated"
            #     for user in project_update_push:
            #         director = User.objects.get(pk=user.user_id)
            #         registration_ids.append(director.fcm_key)
            #     result = push_service.multiple_devices_data_message(registration_ids=registration_ids,data_message=data_message)
            #     print(result)


    return JsonResponse({"status": "push notification send successfully"}, safe=False)


class StatusByDayView(CreateAPIView):
    def post(self, request, *args, **kwargs):

        today_date = datetime.datetime.now()
        seven_days_before = today_date.date()-timedelta(days=7)
        all_project_status = Project_Status.objects.filter(Q(created_at__gte = seven_days_before), Q(created_at__lte = today_date)).order_by('-created_at')

        project_status_list = list()
        for project_status in all_project_status:
            project = Project_Info.objects.get(pk=project_status.project_id)
            user = User.objects.get(pk=project_status.user_id)
            start_date = str(project_status.created_at)
            start_date = start_date.split('+')
            start_date = dateutil.parser.parse(start_date[0])
            end_date = datetime.datetime.now()
            duration = str(end_date - start_date)
            # print("kkkkkkkkkkkkkkkkkkkkkk")
            # print(duration)
            # print(duration.days)
            # print(duration.hours)
            # print(duration.minutes)
            # print(duration.seconds)
            project_status_list.append(
                {
                    'project_id': project_status.project_id,
                    'project_name': project.title,
                    'user_id': project_status.user_id,
                    'user_name': user.username,
                    'status': project_status.status,
                    'time': duration,
                    # 'time_from_now':str(time_difference.days)+":"+str(time_difference.hours)+":"+str(time_difference.minute)+":"+str(time_difference.second),
                }
            )
        return JsonResponse({'message': 'success', 'status_code': '200', 'data': project_status_list})

class LogoutView(CreateAPIView):

    def post(self, request, *args, **kwargs):
        if 'user_id' not in request.POST or request.POST['user_id'] is '':
            raise ValidationError({'message': 'User ID is needed', 'status_code': '400'})



        try:
            user_details = User.objects.get(pk=request.POST['user_id'])
            user_details.fcm_key=""
            user_details.save()



            return Response(
                {'message': 'success', 'status_code': '200'})




        except User.DoesNotExist:
            return Response({'message': 'Failed', 'status_code': '400', 'status': 'User does not exist'})


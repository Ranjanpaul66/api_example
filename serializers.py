from rest_framework import serializers
from users.models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'is_active','user_role','user_name')

class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project_Info
        fields = ('title', 'code', 'team_size', 'duration', 'response_day', 'budget', 'revenue_plan', 'target_revenue', 'additional_cost', 'type', 'details')
class ProjectManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_Manager
        fields = ('project_id', 'assigned_by', 'assigned_to', 'created_at', 'modified_at', 'created_by', 'modified_by', 'status')

class ProjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_Type
        fields = (
        'name', 'code', 'details', 'create  d_at', 'modified_at', 'created_by', 'modified_by', 'status')
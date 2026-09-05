from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from config.geo_utils import linestring_from_points
from geolocation.models import DriverTrajectory
from geolocation.serializers import (
    TrajectoryCreateSerializer,
    TrajectorySerializer,
    TrajectoryUpdateSerializer,
)


def _get_driver(driver_id: int):
    return User.objects.filter(pk=driver_id).first()


class TrajectoryListCreateView(APIView):
    @extend_schema(responses={200: TrajectorySerializer(many=True)}, tags=['Driver Trajectories'])
    def get(self, request, driver_id):
        if _get_driver(driver_id) is None:
            return Response({'detail': 'Driver not found'}, status=404)
        qs = DriverTrajectory.objects.filter(driver_id=driver_id).order_by('-updated_at')
        active = request.query_params.get('active')
        if active == 'true':
            qs = qs.filter(is_active=True)
        return Response(TrajectorySerializer(qs, many=True).data)

    @extend_schema(request=TrajectoryCreateSerializer, responses={201: TrajectorySerializer}, tags=['Driver Trajectories'])
    def post(self, request, driver_id):
        if _get_driver(driver_id) is None:
            return Response({'detail': 'Driver not found'}, status=404)
        ser = TrajectoryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        trajectory = DriverTrajectory.objects.create(
            driver_id=driver_id,
            name=data.get('name') or '',
            geometry=linestring_from_points(data['points']),
            tolerance_meters=data.get('tolerance_meters', 500),
        )
        return Response(TrajectorySerializer(trajectory).data, status=status.HTTP_201_CREATED)


class TrajectoryActiveView(APIView):
    @extend_schema(responses={200: TrajectorySerializer}, tags=['Driver Trajectories'])
    def get(self, request, driver_id):
        if _get_driver(driver_id) is None:
            return Response({'detail': 'Driver not found'}, status=404)
        trajectory = (
            DriverTrajectory.objects
            .filter(driver_id=driver_id, is_active=True)
            .order_by('-updated_at')
            .first()
        )
        if trajectory is None:
            return Response({'detail': 'No active trajectory'}, status=404)
        return Response(TrajectorySerializer(trajectory).data)


class TrajectoryDetailView(APIView):
    def _get_trajectory(self, driver_id, trajectory_id):
        return DriverTrajectory.objects.filter(
            pk=trajectory_id, driver_id=driver_id,
        ).first()

    @extend_schema(request=TrajectoryUpdateSerializer, responses={200: TrajectorySerializer}, tags=['Driver Trajectories'])
    def put(self, request, driver_id, trajectory_id):
        trajectory = self._get_trajectory(driver_id, trajectory_id)
        if trajectory is None:
            return Response({'detail': 'Trajectory not found'}, status=404)
        ser = TrajectoryUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if 'name' in data:
            trajectory.name = data['name']
        if 'points' in data:
            trajectory.geometry = linestring_from_points(data['points'])
        if 'tolerance_meters' in data:
            trajectory.tolerance_meters = data['tolerance_meters']
        if 'is_active' in data:
            trajectory.is_active = data['is_active']
        trajectory.save()
        return Response(TrajectorySerializer(trajectory).data)

    @extend_schema(responses={200: dict}, tags=['Driver Trajectories'])
    def delete(self, request, driver_id, trajectory_id):
        trajectory = self._get_trajectory(driver_id, trajectory_id)
        if trajectory is None:
            return Response({'detail': 'Trajectory not found'}, status=404)
        trajectory.is_active = False
        trajectory.save(update_fields=['is_active', 'updated_at'])
        return Response({'detail': 'Trajectory deactivated', 'id': trajectory_id})

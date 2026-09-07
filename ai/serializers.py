from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField(max_length=4000)


class ChatRequestSerializer(serializers.Serializer):
    messages = ChatMessageSerializer(many=True, min_length=1)
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)


class ParseRideRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, help_text='Demande en langage naturel')
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)


class ResolveDestinationRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=['pickup', 'destination'],
        default='destination',
        help_text='Résoudre comme point de départ ou d\'arrivée',
    )


class DriverBriefingRequestSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)


class ClassifySOSRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')
    emergency_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    location = serializers.DictField(required=False, allow_null=True)

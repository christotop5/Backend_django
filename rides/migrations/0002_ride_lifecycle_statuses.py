# Generated migration — ride lifecycle statuses

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rides', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ride',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_approval', 'Pending driver approval'),
                    ('approved', 'Driver approved'),
                    ('passenger_arrived', 'Passenger at pickup'),
                    ('in_trip', 'In trip'),
                    ('awaiting_payment', 'Awaiting payment'),
                    ('completed', 'Completed'),
                    ('rejected', 'Rejected'),
                    ('cancelled', 'Cancelled'),
                    ('searching', 'Searching'),
                    ('matched', 'Matched'),
                    ('en_route', 'En route'),
                ],
                default='pending_approval',
                max_length=20,
            ),
        ),
    ]

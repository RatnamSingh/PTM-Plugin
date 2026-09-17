from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('ptm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ptmslot',
            name='dyte_meeting_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

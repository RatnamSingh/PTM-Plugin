from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('ptm', '0002_ptmslot_dyte_meeting_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ptmbooking',
            name='parent_id',
            field=models.CharField(db_index=True, help_text='External ID of the parent', max_length=100),
        ),
        migrations.AlterField(
            model_name='ptmbooking',
            name='student_id',
            field=models.CharField(db_index=True, help_text='External ID of the student', max_length=100),
        ),
        migrations.AlterField(
            model_name='ptmbooking',
            name='tenant_id',
            field=models.CharField(db_index=True, help_text='ID of the school/ERP tenant', max_length=100),
        ),
        migrations.AlterField(
            model_name='ptmevent',
            name='tenant_id',
            field=models.CharField(db_index=True, help_text='ID of the school/ERP tenant', max_length=100),
        ),
        migrations.AlterField(
            model_name='ptmslot',
            name='teacher_id',
            field=models.CharField(db_index=True, help_text='External ID of the teacher', max_length=100),
        ),
        migrations.AlterField(
            model_name='ptmslot',
            name='tenant_id',
            field=models.CharField(db_index=True, help_text='ID of the school/ERP tenant', max_length=100),
        ),
    ]

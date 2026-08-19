from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import django.utils.timezone

class Migration(migrations.Migration):
    initial=True
    dependencies=[('sales','0004_link_requests_to_quotations'),('staff','0001_initial'),('products','0001_initial'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name='ProductionJob',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('job_no',models.CharField(editable=False,max_length=30,unique=True)),
            ('station',models.CharField(choices=[('laser','Acrylic Laser Cutting'),('cnc','Wood CNC Cutting'),('memento','Memento / Trophy'),('wall_decor','Wall Décor'),('wood_craft','Wood Craft & Polishing'),('resin','Resin Products'),('custom','Customized Products')],max_length=30)),
            ('stage',models.CharField(choices=[('planning','Planning'),('material','Material Allocation'),('design_check','Design Check'),('production','Production'),('finishing','Finishing'),('qc_pending','Quality Check Pending'),('completed','Completed')],default='planning',max_length=30)),
            ('status',models.CharField(choices=[('pending','Pending'),('assigned','Assigned'),('in_progress','In Progress'),('on_hold','On Hold'),('completed','Completed'),('cancelled','Cancelled')],default='pending',max_length=20)),
            ('priority',models.CharField(choices=[('normal','Normal'),('high','High'),('urgent','Urgent')],default='normal',max_length=20)),
            ('deadline',models.DateField(blank=True,null=True)),('started_at',models.DateTimeField(blank=True,null=True)),('completed_at',models.DateTimeField(blank=True,null=True)),
            ('progress_percent',models.PositiveSmallIntegerField(default=0,validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
            ('safety_checked',models.BooleanField(default=False)),('design_checked',models.BooleanField(default=False)),('material_ready',models.BooleanField(default=False)),('notes',models.TextField(blank=True)),
            ('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),
            ('assigned_staff',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='production_jobs',to='staff.staffprofile')),
            ('created_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='created_production_jobs',to=settings.AUTH_USER_MODEL)),
            ('order',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='production_jobs',to='sales.salesorder')),
        ],options={'ordering':['status','deadline','-created_at'],'indexes':[models.Index(fields=['status','deadline'],name='production__status_8a6d45_idx'),models.Index(fields=['station','status'],name='production__station_3cf86f_idx'),models.Index(fields=['assigned_staff','status'],name='production__assign_1e8d3a_idx')]}),
        migrations.CreateModel(name='ProductionProgress',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('stage',models.CharField(choices=[('planning','Planning'),('material','Material Allocation'),('design_check','Design Check'),('production','Production'),('finishing','Finishing'),('qc_pending','Quality Check Pending'),('completed','Completed')],max_length=30)),('progress_percent',models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0)])),('note',models.TextField(blank=True)),('created_at',models.DateTimeField(auto_now_add=True)),
            ('job',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='progress_updates',to='production.productionjob')),('updated_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
        ],options={'ordering':['-created_at']}),
        migrations.CreateModel(name='ProductionMaterial',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('material_name',models.CharField(max_length=180)),('quantity_required',models.DecimalField(decimal_places=2,max_digits=12,validators=[django.core.validators.MinValueValidator(0)])),('unit',models.CharField(default='Piece',max_length=40)),('issued_quantity',models.DecimalField(decimal_places=2,default=0,max_digits=12,validators=[django.core.validators.MinValueValidator(0)])),('notes',models.TextField(blank=True)),('created_at',models.DateTimeField(auto_now_add=True)),
            ('job',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='materials',to='production.productionjob')),('product',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='production_materials',to='products.product')),
        ]),
        migrations.CreateModel(name='ProductionIssue',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('issue_type',models.CharField(choices=[('delay','Delay'),('rework','Rework')],max_length=20)),('stage',models.CharField(choices=[('planning','Planning'),('material','Material Allocation'),('design_check','Design Check'),('production','Production'),('finishing','Finishing'),('qc_pending','Quality Check Pending'),('completed','Completed')],max_length=30)),('reason',models.TextField()),('corrective_action',models.TextField(blank=True)),('occurred_at',models.DateTimeField(default=django.utils.timezone.now)),('resolved',models.BooleanField(default=False)),('resolved_at',models.DateTimeField(blank=True,null=True)),('created_at',models.DateTimeField(auto_now_add=True)),
            ('created_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),('job',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='issues',to='production.productionjob')),('staff',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to='staff.staffprofile')),
        ]),
    ]

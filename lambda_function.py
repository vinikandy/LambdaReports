import boto3
import boto3.ec2
import json

ec2 = boto3.client('ec2')
sqs = boto3.resource('sqs')
iam = boto3.client('iam')
rds = boto3.client('rds')
ct = boto3.client('cloudtrail')
cfg = boto3.client('config')
sns = boto3.client('sns')
s3 = boto3.resource('s3')

# resource report
def lambda_handler(event, context): 
    infra_report=get_vpc_details()
    infra_report.update(get_iam_roles_policies())
    infra_report.update(cloudtrail_check())
    infra_report.update(config_check())
    infra_report.update(list_buckets())
    infra_report.update(list_rds_instances())
    

    #  posting json to sqs 
    queue = sqs.get_queue_by_name(QueueName='lambda-reports-queue')
    response = queue.send_message(MessageBody=json.dumps(infra_report))
    
# return dictionary     
def report(report_name,report_value):
        report_str={report_name:report_value}
        return report_str

# Region, VPC, subnet & EC2 details    
def get_vpc_details():
        regions_lst = ec2.describe_regions()['Regions']
        region_names = [d['RegionName'] for d in regions_lst]
        region_report={}
        vpc_report=[]
        subnets_cnt_report={}
        subnet_details_report=[]
        ec2_cnt_report={}
        ec2_details_report=[]
        for r in region_names:
            ec2r = boto3.resource('ec2', region_name=r) 
            vpc_lst=[]
            for v1 in ec2r.vpcs.all():
                vpc_lst.append(v1.id)
            no_of_vpc=len(vpc_lst)
            # Number of vpc's in a region report
            region_report.update(report(r,no_of_vpc))

            for v_id in vpc_lst:
                vpc = ec2r.Vpc(v_id)

              # route table details
                routetbl_lst=[]
                for r1 in vpc.route_tables.all():
                    routetbl_lst.append(r1.id)
                for r_id in routetbl_lst:
                    route_tbl=ec2r.RouteTable(r_id)
                    x={"vpc_id:":vpc.vpc_id," cidr":vpc.cidr_block,"tenancy":vpc.instance_tenancy,"state":vpc.state,"route table id":route_tbl.route_table_id}
                    vpc_report.append(x)
                
              # subnet details
                subnet_lst=[]
                for s1 in vpc.subnets.all():
                    subnet_lst.append(s1.id)
                no_of_subnets=len(subnet_lst)
                subnets_cnt_report.update(report(vpc.vpc_id,no_of_subnets))
                for s_id in subnet_lst:
                    subnet=ec2r.Subnet(s_id)
                    y={"vpc_id":vpc.vpc_id,"subnet_id":subnet.id,"cidr":subnet.cidr_block,"public":subnet.map_public_ip_on_launch,"state":subnet.state}
                    subnet_details_report.append(y)
                    
                    # ec2 details
                    ec2_lst=[]
                    for e1 in subnet.instances.all():
                        ec2_lst.append(e1.id)
                    no_of_instances=len(ec2_lst)
                    ec2_cnt_report.update(report(subnet.id,no_of_instances))
                    for ec2_id in ec2_lst:
                        instance=ec2r.Instance(ec2_id)
                        
                        # ec2 volume details
                        volume_lst=[]
                        for vol in instance.volumes.all():
                            volume_lst.append(vol.id)
                        for vol_id in volume_lst:
                            volume=ec2r.Volume(vol_id)
                            z={"vpc_id":instance.vpc_id,"subnet_id":instance.subnet_id,"Instance id":instance.instance_id,"AMI id":instance.image_id,"created on":str(instance.launch_time),"instance type":instance.instance_type,"Security Groups":instance.security_groups,"Volume type":volume.volume_type,"volume size":volume.size}
                            ec2_details_report.append(z)

        return{"Number of VPC in a region Report":region_report,"VPC details Report":vpc_report,"Number of subntes in a VPC Report":subnets_cnt_report,"subnet details Report":subnet_details_report,"Number of Instances in a subnet Report":ec2_cnt_report,"ec2 details Report":ec2_details_report}          

#list number of iam roles and attached policies
def get_iam_roles_policies():
        roles_cnt_report={}
        policy_cnt_report={}
        role_dtls= iam.list_roles()
        role_lst=[]
        i=0
        for rls in role_dtls['Roles']:
            role_lst.append(rls['RoleName'])
            policy_dtls=iam.list_attached_role_policies(RoleName=role_lst[i])
            policy_lst=policy_dtls['AttachedPolicies']
            policy_cnt_report.update(report(role_lst[i],len(policy_lst)))
            i=i+1
        return{"Number of Roles":len(role_lst),"Number of attached policies to a role":policy_cnt_report}
    
    
# List  CloudTrail is enabled or not
def cloudtrail_check():
        cloud_details_report=[]
        ct_lst=ct.describe_trails()['trailList']
        for ct_name in ct_lst:
            cloud_trail_status = ct.get_trail_status(Name=ct_name['Name'])
            if cloud_trail_status['IsLogging'] == True:
                ct_status = "Enabled"
            else:
                ct_status = "Not Enabled"
            x={"cloud trail":ct_name['Name'],"status":ct_status}
            cloud_details_report.append(x)
        return{"cloud trail Report":cloud_details_report}       

# List  Config is on or not
def config_check():
        config_details_report=[]
        cfg_lst=cfg.get_discovered_resource_counts()['resourceCounts']
        for cfg_type in cfg_lst:
            x={"config is on for":cfg_type['resourceType'],"Number of resources":cfg_type['count']}
            config_details_report.append(x)
        return{"config Report":config_details_report}    

    
#list of s3 buckets
def list_buckets():
        bucket_list=[]
        for bucket in s3.buckets.all():
            bucket_list.append(bucket.name)
        return{"bucket list":bucket_list} 
        
#list of rds instances
def list_rds_instances():
        rds_response = rds.describe_db_instances()['DBInstances']
        rds_lst = []
        for rid in rds_response:
            rds_lst.append(rid['DBInstanceIdentifier'])
        return{"RDS Instance list":rds_lst}     
   
 
    
   

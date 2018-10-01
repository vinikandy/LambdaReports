import boto3
import boto3.ec2
import json

# calling sns service in boto3
ec2 = boto3.client('ec2')
iam = boto3.client('iam')
ct = boto3.client('cloudtrail')
cfg = boto3.client('config')
s3 = boto3.resource('s3')
rds = boto3.client('rds')

def lambda_handler(event, context):

    # sqs
    queue = sqs.get_queue_by_name(QueueName='lambda-reports-queue')
    

    # Retrieves all regions/endpoints that work with EC2
    regions_list = ec2.describe_regions()['Regions']
    #print(type(regions_list))
    region_names = [d['RegionName'] for d in regions_list]
    print()


    # VPC details
    for r in region_names:
        response = queue.send_message(MessageBody=json.dumps(print("Region: ",r)))
        ec2r = boto3.resource('ec2', region_name=r)
        vpc_lst=[]
        for v1 in ec2r.vpcs.all():
            vpc_lst.append(v1.id)
        no_of_vpc=len(vpc_lst)
        print("number of vpcs in region :",r," are:",no_of_vpc)
        for v_id in vpc_lst:
            vpc = ec2r.Vpc(v_id)
            print("vpc_id:",vpc.vpc_id," cidr: ",vpc.cidr_block," tenancy: ",vpc.instance_tenancy," state: ",vpc.state)
            # route table details
            routetbl_lst=[]
            for r1 in vpc.route_tables.all():
                routetbl_lst.append(r1.id)
            for r_id in routetbl_lst:
                route_tbl=ec2r.RouteTable(r_id)
                print("vpc_id: ",route_tbl.vpc_id," Route table id: ",route_tbl.route_table_id)
            # subnet details
            subnet_lst=[]
            for s1 in vpc.subnets.all():
                subnet_lst.append(s1.id)
            no_of_subnets=len(subnet_lst)
            print("number of subnets under vpc :",vpc.vpc_id," are:",no_of_subnets)
            for s_id in subnet_lst:
                subnet=ec2r.Subnet(s_id)
                print("subnet_id: ",subnet.id," cidr: ",subnet.cidr_block," Public: ",subnet.map_public_ip_on_launch," State: ",subnet.state)
                # ec2 details
                ec2_lst=[]
                for e1 in subnet.instances.all():
                    ec2_lst.append(e1.id)
                no_of_instances=len(ec2_lst)
                print("number of instances under subnet :",subnet.id," are:",no_of_instances)
                for ec2_id in ec2_lst:
                    instance=ec2r.Instance(ec2_id)
                    # route table details
                    volume_lst=[]
                    for vol in instance.volumes.all():
                        volume_lst.append(vol.id)
                    for vol_id in volume_lst:
                        volume=ec2r.Volume(vol_id)
                        print("vpc_id: ",instance.vpc_id," subnet_id: ",instance.subnet_id," Instance id: ",instance.instance_id," AMI id: ",instance.image_id," created on: ",instance.launch_time," instance type: ",instance.instance_type," Security Groups: ",instance.security_groups," Volume type: ",volume.volume_type," volume size: ",volume.size)
            print()

    #list number of iam roles and attached policies
    role_dtls= iam.list_roles()
    role_lst=[]
    i=0
    for rls in role_dtls['Roles']:
        role_lst.append(rls['RoleName'])
        policy_dtls=iam.list_attached_role_policies(RoleName=role_lst[i])
        policy_lst=policy_dtls['AttachedPolicies']
        print("Nuumber of attached policies to role ",role_lst[i]," is: ",len(policy_lst))
        i=i+1
    print("\nTotal Number of IAM Roles: ",len(role_lst),"\n")   
    
    # List if CloudTrail is enabled or not
    ct_lst=ct.describe_trails()['trailList']
    for ct_name in ct_lst:
        cloud_trail_status = ct.get_trail_status(Name=ct_name['Name'])
        if cloud_trail_status['IsLogging'] == True:
            ct_status = "Enabled"
        else:
            ct_status = "Not Enabled"
        print("cloud trail <",ct_name['Name'],"> status is : ",ct_status)

    # List if Config is on or not
    cfg_lst=cfg.get_discovered_resource_counts()['resourceCounts']
    for cfg_type in cfg_lst:
        print("config is on for :",cfg_type['resourceType']," Number of resources ",cfg_type['count'])
        
    #list of s3 buckets
    for bucket in s3.buckets.all():
        print(bucket.name)

    #list of rds instances
    rds_response = rds.describe_db_instances()['DBInstances']
    rds_lst = []
    for rid in rds_response:
        rds_lst.append(rid['DBInstanceIdentifier'])
    print(rds_lst)

    
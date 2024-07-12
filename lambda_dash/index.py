import boto3 # type: ignore
import json
import os

# ================================================================
#                       Variáveis Globais
# ================================================================
AWS_REGION = boto3.session.Session().region_name
ALB_CLIENT = boto3.client('elbv2')
ECS_CLIENT = boto3.client('ecs')
RDS_CLIENT = boto3.client('rds')
CLOUDWATCH_CLIENT = boto3.client('cloudwatch')
# ================================================================
#           Função principal para montar o dashboard
# ================================================================

def lambda_handler(event, context):
    # Variáveis de identificação
    ENV = os.environ['ENV']
    CUSTOMER_NAME = os.environ['CUSTOMER_NAME']
    
    RDS_NAMES = create_services_names(str(os.environ['RDS_NAMES']))
    ECS_CLUSTERS = create_services_names(str(os.environ['ECS_CLUSTERS']))
    REDIS_NAMES = create_services_names(str(os.environ['REDIS_NAMES']))
    LOAD_BALANCER_NAMES = create_services_names(str(os.environ['LOAD_BALANCER_NAMES']))

    # Criar dashboard
    response = create_full_dashboard(LOAD_BALANCER_NAMES, RDS_NAMES, ECS_CLUSTERS, REDIS_NAMES, ENV, CUSTOMER_NAME)
    
# ================================================================
#              FUNÇÃO PARA SEPARAR NOME DOS SERVIÇOS
# ================================================================ 
def create_services_names(service):
    if "," not in service:
        return [service]  
    return service.split(",")

# ================================================================
#                   LOAD BALANCER METRICS
# ================================================================
def create_alb_dashboard(LOAD_BALANCER_NAMES):
    widgets = []

    # Add header text widget
    alb_header_widget = {
        "height": 2,
        "width": 24,
        "y": 0,
        "x": 0,
        "type": "text",
        "properties": {                                                                        
            "markdown": f"# **Load Balancer Metrics**\n\n" + "\n".join([f"[button:primary:{name}](https://{AWS_REGION}.console.aws.amazon.com/ec2/home?region={AWS_REGION}#LoadBalancer:loadBalancerArn={get_alb_arn(name)};tab=listeners)" for name in LOAD_BALANCER_NAMES]),
            "background": "transparent"
        }
    }
    widgets.append(alb_header_widget)

    for i, LOAD_BALANCER_NAME in enumerate(LOAD_BALANCER_NAMES):
        # Add text widget for ALB name
        text_widget = {
            "height": 1,
            "width": 24,
            "y": 2 + (i * 7),  
            "x": 0,
            "type": "text",
            "properties": {
                "markdown": f"## {LOAD_BALANCER_NAME}",
                "background": "transparent"
            }
        }
        widgets.append(text_widget)

        metrics = get_metrics_for_alb(LOAD_BALANCER_NAME)
        
        for index, metric in enumerate(metrics):
            widget = {
                "type": "metric",
                "x": (index % 5) * 5,
                "y": (index // 5) * 8 + 3 + (i * 8),  
                "width": metric["width"],
                "height": 6,
                "properties": {
                    "metrics": metric["metrics"],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": AWS_REGION,
                    "period": metric["period"],
                    "title": metric["label"],
                    "annotations": metric.get("annotations", {})
                }
            }
            widgets.append(widget)

    dashboard_body = {
        "widgets": widgets
    }
    
    return dashboard_body

def get_alb_arn(LOAD_BALANCER_NAME):
    return ALB_CLIENT.describe_load_balancers(Names=[LOAD_BALANCER_NAME])['LoadBalancers'][0]['LoadBalancerArn']

def get_metrics_for_alb(LOAD_BALANCER_NAME):
    target_groups = get_target_groups(LOAD_BALANCER_NAME)
    alb_arn = get_alb_arn(LOAD_BALANCER_NAME)
    alb_arn_shortened = alb_arn.split("/", 1)[-1]

    # Construindo a lista de métricas para os hosts saudáveis de cada grupo de destino
    metrics_for_m4 = []
    for target_group_name in target_groups:
        target_group_arn = get_target_group_arn(target_group_name)
        metric = ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", target_group_arn, "LoadBalancer", alb_arn_shortened]
        metrics_for_m4.append(metric)

    alb_metrics = [
        {
            "id": "m1",
            "label": "[ALB] Request Count",
            "period": 300,
            "yAxis": "left",
            "width": 5,
            "metrics": [
                ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", alb_arn, {"stat": "Sum"}]
            ]
        },
        {
            "id": "m2",
            "label": "[ALB] Response Time",
            "period": 300,
            "yAxis": "left",
            "width": 5,
            "metrics": [
                ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", alb_arn, {"region": AWS_REGION, "stat": "Average"}],
                ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", alb_arn, {"region": AWS_REGION, "stat": "p95"}]
            ]
        },
        {
            "id": "e1",  
            "label": "[ALB] 4XX Errors",
            "expression": "IF(m4>0,100*(m3/m4),0)",
            "period": 300,
            "yAxis": "left",
            "width": 5,
            "metrics": [
                [ { "expression": "IF(m2>m1,100*(m1/m2),0)", "label": "4xx_percent", "id": "e1" } ],
                [ "AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", alb_arn, { "region": AWS_REGION, "id": "m1", "visible": False } ],
                [ ".", "RequestCount", ".", ".", { "stat": "Sum", "region": AWS_REGION, "id": "m2", "visible": False } ]
            ]
        },
        {
            "id": "e1",  
            "label": "[ALB] 5XX Errors",
            "expression": "IF(m4>0,100*(m3/m4),0)",
            "period": 300,
            "yAxis": "left",
            "width": 5,
            "metrics": [
                [ { "expression": "IF(m2>m1,100*(m1/m2),0)", "label": "5xx_percent", "id": "e1" } ],
                [ "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", alb_arn, { "region": AWS_REGION, "id": "m1", "visible": False } ],
                [ ".", "RequestCount", ".", ".", { "stat": "Sum", "region": AWS_REGION, "id": "m2", "visible": False } ]
            ],
            "annotations": {"horizontal": [{"label": "Alarm", "value": 5}]}
        },
        {
            "id": "m4", 
            "label": "[ALB] Health Host",
            "period": 60,
            "yAxis": "left",
            "width": 4,
            "metrics": metrics_for_m4
        }
    ]
    
    return alb_metrics

def get_target_group_arn(target_group_name):
    elbv2_client = boto3.client('elbv2')
    response = elbv2_client.describe_target_groups(Names=[target_group_name])
    if 'TargetGroups' in response and len(response['TargetGroups']) > 0:
        arn_parts = response['TargetGroups'][0]['TargetGroupArn'].split(':')
        return ':'.join(arn_parts[5:])
    else:
        return None

def get_target_groups(LOAD_BALANCER_NAME):
    load_balancer_arn = get_alb_arn(LOAD_BALANCER_NAME)
    response = ALB_CLIENT.describe_target_groups(LoadBalancerArn=load_balancer_arn)

    target_groups = []
    for target_group in response['TargetGroups']:
        target_groups.append(target_group['TargetGroupName'])

    return target_groups

# ================================================================
#                   FULL DASHBOARD
# ================================================================
def create_full_dashboard(LOAD_BALANCER_NAMES, RDS_NAMES, ECS_CLUSTERS, REDIS_NAMES, ENV, CUSTOMER_NAME):
    dashboard_body = create_alb_dashboard(LOAD_BALANCER_NAMES)

    try:
        dashboard_name = f'{ENV}-{CUSTOMER_NAME}-Complete-Dashboard'
        response = CLOUDWATCH_CLIENT.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        return response
    except Exception as e:
        print("Erro ao criar o dashboard:", e)
        return None
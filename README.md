# EFS_ResponseMeasurement
EFSのファイルRead/Writreレスポンス測定

# 検証環境準備
## (1)事前設定
### (1)-(a) 作業環境の準備
下記を準備します。
* bashが利用可能な環境(LinuxやMacの環境)
* gitがインストールされていること
* aws-cliのセットアップ
* AdministratorAccessポリシーが付与され実行可能な、aws-cliのProfileの設定
*
### (1)-(b)ツールのclone
環境構築様に資源をcloneする
```shell
git clone https://github.com/Noppy/EFS_ResponseMeasurement.git
cd EFS_ResponseMeasurement/
```

### (1)-(c) CLI実行用の事前準備
これ以降のAWS-CLIで共通で利用するパラメータを環境変数で設定しておきます。
```shell
export PROFILE="<設定したプロファイル名称を指定。デフォルトの場合はdefaultを設定>"
export REGION=ap-northeast-1
```

## (2)VPCやBasion環境の作成(CloudFormation利用)
### (2)-(a)VPC作成
私が作成し利用しているVPC作成用のCloudFormationテンプレートを利用します。まず、githubからテンプレートをダウンロードします。
```shell
curl -o vpc-4subnets.yaml https://raw.githubusercontent.com/Noppy/CfnCreatingVPC/master/vpc-4subnets.yaml
```
ダウンロードしたテンプレートを利用し、VPCをデプロイします。
```shell
CFN_STACK_PARAMETERS='
[
  {
    "ParameterKey": "DnsHostnames",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "DnsSupport",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "InternetAccess",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "EnableNatGW",
    "ParameterValue": "false"
  },
  {
    "ParameterKey": "VpcName",
    "ParameterValue": "EFSTestVPC"
  },
  {
    "ParameterKey": "VpcInternalDnsName",
    "ParameterValue": "efstest.local."
  }
]'

# Create Stack
aws --profile ${PROFILE} --region ${REGION} cloudformation create-stack \
    --stack-name EFSTestVPC \
    --template-body "file://./vpc-4subnets.yaml" \
    --parameters "${CFN_STACK_PARAMETERS}" \
    --capabilities CAPABILITY_IAM ;

# Wait
aws --profile ${PROFILE} --region ${REGION} cloudformation wait \
    stack-create-complete --stack-name EFSTestVPC

```

### (2)-(b) 構成情報取得
```shell
#構成情報取得
VPCID=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`VpcId`].[OutputValue]')

VPC_CIDR=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`VpcCidr`].[OutputValue]')

PublicSubnet1Id=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PublicSubnet1Id`].[OutputValue]')

PublicSubnet2Id=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PublicSubnet2Id`].[OutputValue]')

PrivateSubnet1Id=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PrivateSubnet1Id`].[OutputValue]')

PrivateSubnet2Id=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PrivateSubnet2Id`].[OutputValue]')

PrivateSubnet1RouteTableId=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PrivateSubnet1RouteTableId`].[OutputValue]')

PrivateSubnet2RouteTableId=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    cloudformation describe-stacks \
        --stack-name EFSTestVPC \
        --query 'Stacks[].Outputs[?OutputKey==`PrivateSubnet2RouteTableId`].[OutputValue]')

echo -e "VPCID=$VPCID\nVPC_CIDR=$VPC_CIDR\nPublicSubnet1Id =$PublicSubnet1Id\nPublicSubnet2Id =$PublicSubnet2Id\nPrivateSubnet1Id=$PrivateSubnet1Id\nPrivateSubnet2Id=$PrivateSubnet2Id\nPrivateSubnet1RouteTableId=$PrivateSubnet1RouteTableId \nPrivateSubnet2RouteTableId=$PrivateSubnet2RouteTableId"
```

## (3)EFSおよびインスタンス作成
### (3)-(a) Security Group作成
```shell
#NFSClient用SG作成
CLIENT_SG_ID=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    ec2 create-security-group \
        --group-name ClientSG \
        --description "Allow ssh" \
        --vpc-id ${VPCID}) ;

aws --profile ${PROFILE} --region ${REGION} \
    ec2 create-tags \
        --resources ${VCLIENT_SG_ID} \
        --tags "Key=Name,Value=ClientSG" ;

aws --profile ${PROFILE} --region ${REGION}  \
    ec2 authorize-security-group-ingress \
        --group-id ${CLIENT_SG_ID} \
        --protocol tcp \
        --port 22 \
        --cidr '0.0.0.0/0' ;

#NFSServer用SG作成
SERVER_SG_ID=$(aws --profile ${PROFILE} --region ${REGION}  --output text \
    ec2 create-security-group \
        --group-name ServerSG \
        --description "Allow all traffics" \
        --vpc-id ${VPCID}) ;

aws --profile ${PROFILE} --region ${REGION} \
    ec2 create-tags \
        --resources ${SERVER_SG_ID} \
        --tags "Key=Name,Value=ServerSG" ;

aws --profile ${PROFILE} --region ${REGION} \
    ec2 authorize-security-group-ingress \
        --group-id ${SERVER_SG_ID} \
        --protocol all \
        --source-group ${CLIENT_SG_ID} ;
```

### (3)-(b) NFSクライアントに付与するIAMロールの作成
```shell
POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
#IAMロールの作成
aws --profile ${PROFILE} \
    iam create-role \
        --role-name "Ec2-NFSClientRole" \
        --assume-role-policy-document "${POLICY}" \
        --max-session-duration 43200

# ReadOnlyAccessのアタッチ
aws --profile ${PROFILE} \
    iam attach-role-policy \
        --role-name "Ec2-NFSClientRole" \
        --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

#インスタンスプロファイルの作成
aws --profile ${PROFILE} \
    iam create-instance-profile \
        --instance-profile-name "Ec2-NFSClientRole-Profile";

aws --profile ${PROFILE} \
    iam add-role-to-instance-profile \
        --instance-profile-name "Ec2-NFSClientRole-Profile" \
        --role-name "Ec2-NFSClientRole" ;
```

### (3)-(c) Client/Serverインスタンスの作成
#### (3)-(c)-(i)初期設定
```shell
#キーペアの設定
KEYNAME="CHANGE_KEY_PAIR_NAME"  #環境に合わせてキーペア名を設定してください。  

#最新のAmazon Linux2のAMI IDを取得します。
AL2_AMIID=$(aws --profile ${PROFILE} --region ${REGION} --output text \
    ec2 describe-images \
        --owners amazon \
        --filters 'Name=name,Values=amzn2-ami-hvm-2.0.????????.?-x86_64-gp2' \
                  'Name=state,Values=available' \
        --query 'reverse(sort_by(Images, &CreationDate))[:1].ImageId' ) ;

#セキュリティーグループの取得
#Security Group ID取得
CLIENT_SG_ID=$(aws --profile ${PROFILE} --region ${REGION} --output text \
        ec2 describe-security-groups \
                --filter 'Name=group-name,Values=ClientSG' \
        --query 'SecurityGroups[].GroupId');

SERVER_SG_ID=$(aws --profile ${PROFILE} --region ${REGION} --output text \
        ec2 describe-security-groups \
                --filter 'Name=group-name,Values=ServerSG' \
        --query 'SecurityGroups[].GroupId');

#確認
echo -e "KEYNAME=${KEYNAME}\nAL2_AMIID=${AL2_AMIID}\nCLIENT_SG_ID=${CLIENT_SG_ID}\nSERVER_SG_ID=${SERVER_SG_ID}"
```
#### (3)-(c)-(ii)クライアントインスタンスの作成
```shell
#インスタンスタイプ設定
#INSTANCE_TYPE="t2.micro"
INSTANCE_TYPE="m5d.xlarge"

#タグ設定
TAGJSON='
[
    {
        "ResourceType": "instance",
        "Tags": [
            {
                "Key": "Name",
                "Value": "NFS-Client"
            }
        ]
    }
]'

#ユーザデータ設定
USER_DATA='
#!/bin/bash -xe
                
yum -y update
yum -y install nfs-utils
hostnamectl set-hostname NFS-Client
'
# インスタンスの起動
aws --profile ${PROFILE} --region ${REGION} \
    ec2 run-instances \
        --image-id ${AL2_AMIID} \
        --instance-type ${INSTANCE_TYPE} \
        --key-name ${KEYNAME} \
        --subnet-id ${PublicSubnet1Id} \
        --security-group-ids ${CLIENT_SG_ID}\
        --associate-public-ip-address \
        --tag-specifications "${TAGJSON}" \
        --user-data "${USER_DATA}" \
        --iam-instance-profile "Name=Ec2-NFSClientRole-Profile" ;
```

#### (3)-(c)-(iii)サーバインスタンスの作成
```shell
TAGJSON='
[
    {
        "ResourceType": "instance",
        "Tags": [
            {
                "Key": "Name",
                "Value": "NFS-Server"
            }
        ]
    }
]'

#ユーザデータ設定
USER_DATA='
#!/bin/bash -xe
                
yum -y update
hostnamectl set-hostname NFS-Server

#Setup NFS Server
yum install -y nfs-utils
mkdir -p /exports
chown nobody.nobody /exports
chmod 777 /exports
cat <<EOF > /etc/exports
/exports *(rw)
EOF
systemctl enable nfs-server --now
firewall-cmd --add-service nfs
firewall-cmd --runtime-to-permanent
'

aws --profile ${PROFILE} --region ${REGION} \
    ec2 run-instances \
        --image-id ${AL2_AMIID} \
        --instance-type ${INSTANCE_TYPE} \
        --key-name ${KEYNAME} \
        --subnet-id ${PrivateSubnet1Id} \
        --security-group-ids ${SERVER_SG_ID}\
        --associate-public-ip-address \
        --tag-specifications "${TAGJSON}" \
        --user-data "${USER_DATA}" ;
```

### (4) EFSの作成
```shell
#事前情報の取得
SERVER_SG_ID=$(aws --profile ${PROFILE} --region ${REGION} --output text \
        ec2 describe-security-groups \
                --filter 'Name=group-name,Values=ServerSG' \
        --query 'SecurityGroups[].GroupId');

#確認
echo -e "SERVER_SG_ID=${SERVER_SG_ID}"

#　Create File system
EFS_FS_ID=$(aws --profile ${PROFILE} --region ${REGION} --output text \
    efs create-file-system \
        --creation-token "FileSystemForWalkthrough1" \
        --performance-mode "generalPurpose" \
        --tags "Key=Name,Value=EFSTestFileSystem" \
    --query 'FileSystemId' )

# Create Target
aws --profile ${PROFILE} --region ${REGION} \
    efs create-mount-target \
        --file-system-id ${EFS_FS_ID} \
        --subnet-id ${PrivateSubnet1Id} \
        --security-groups ${SERVER_SG_ID}

#下記のEFS Filesystem IDをメモしておく
echo "EFS_FS_ID=${EFS_FS_ID}"
```
### (5) NFSクライアント
### (5)-(1) NFSクライアントの接続とCLIの初期化
#### (5)-(1)-(i)NFSクライアントの接続
```shell
ClientIP=$(aws --profile ${PROFILE} --region ${REGION} --output text \
    ec2 describe-instances  \
        --filters "Name=tag:Name,Values=NFS-Client" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].PublicIpAddress' )

ssh-add
ssh -A ec2-user@${ClientIP}
```
#### (5)-(1)-(ii)CLIの初期化
```shell
# AWS cli初期設定
Region=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed -e 's/.$//')
aws configure set region ${Region}
aws configure set output json
```
### (5)-(2) NFSサーバへのNFS接続
```shell
#EFSのファイルシステムIDの設定( aws efs describe-file-systems で、確認可能)
EFS_FS_ID="<事前にメモしたファイルシステムIDを入力>"

# NFSServerのIP取得
ServerIP=$(aws --output text \
    ec2 describe-instances  \
        --filters "Name=tag:Name,Values=NFS-Server" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].PrivateIpAddress' )

#リージョン情報の取得
Region=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed -e 's/.$//')

#マウントポイントの作成
sudo mkdir /mnt/nfserver
sudo mkdir /mnt/efs

#マウント
cp /etc/fstab ./fstab.tmp
echo "${ServerIP}:/exports /mnt/nfserver nfs defaults 0 0" >> fstab.tmp
echo "${EFS_FS_ID}.efs.${Region}.amazonaws.com:/ /mnt/efs nfs nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"  >> fstab.tmp
sudo cp ./fstab.tmp /etc/fstab
sudo mount -a

#所有者変更
sudo chown  ec2-user:ec2-user /mnt/efs
```
# 検証準備
## (1) 検証ツールの準備
```shell
sudo yum -y install git python3
git clone https://github.com/Noppy/EFS_ResponseMeasurement.git


```
## (2) 検証用データの作成
```shell
dd if=/dev/urandom of=data-0010KiB.dat bs=1024 count=10
dd if=/dev/urandom of=data-0100KiB.dat bs=1024 count=100
dd if=/dev/urandom of=data-1000KiB.dat bs=1024 count=1000
```

## (3) 検証ツール時刻用
```shell



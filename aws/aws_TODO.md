# aws — 예산 확정 후 콘솔/CLI 로 할 일

예산이 확정되기 전에는 이 파일을 읽어두기만 한다. 비용이 나가는 명령은 ★ 표시.
CLI 는 `aws configure` 로 IAM 사용자(루트 아님) 키를 넣은 PC 에서 친다.

## 0. 계정 준비 (돈 안 듦 — 지금 해도 됨)

- 루트 계정 MFA, 작업용 IAM 사용자 생성
- Budgets 알림 $50 / $60, 팀 전원 메일
- EC2 Serial Console 계정 단위 허용 (리전마다)

```bash
aws ec2 enable-serial-console-access --region ap-northeast-2
aws ec2 enable-serial-console-access --region us-east-1
```

## 1. AMI — Ubuntu 26.04 arm64

AMI ID 는 리전마다 다르고 갱신된다. 하드코딩하지 말고 매번 SSM 에서 조회.

```bash
aws ssm get-parameter --region ap-northeast-2 \
  --name /aws/service/canonical/ubuntu/server/26.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
  --query Parameter.Value --output text
```

경로가 안 나오면 콘솔 AMI 카탈로그에서 "Ubuntu Server 26.04 LTS (arm64)" 로 확인.

## 2. Security Group

| SG | 방향 | 포트 | 소스 |
|---|---|---|---|
| sg-sensor | in | 22, 23 | 0.0.0.0/0 |
| sg-sensor | in | 62222 | 내 IP/32, 분석서버 EIP/32 |
| sg-sensor | out | 443 (+ 설치 중엔 80) | 0.0.0.0/0 |
| sg-analysis | in | 62222 | 내 IP/32, 팀원 IP/32 |
| sg-analysis | in | 22 | 내 IP/32 (bootstrap 끝나면 삭제) |
| sg-analysis | out | 전체 | |

센서의 22 인바운드는 `setup.sh cowrie` 전까지는 내 IP 로만 두고, Cowrie 가 22 를 받은 뒤 0.0.0.0/0 으로 연다.
Ubuntu EC2 기본 apt 미러가 http 라 센서 아웃바운드를 443 만 남기면 apt 가 막힌다. 설치 끝난 뒤에 조일 것.

## 3. 인스턴스 ★

```bash
AMI=$(aws ssm get-parameter --region ap-northeast-2 --name /aws/service/canonical/ubuntu/server/26.04/stable/current/arm64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)

aws ec2 run-instances --region ap-northeast-2 \
  --image-id "$AMI" --instance-type t4g.micro \
  --key-name <키페어> --security-group-ids <sg-sensor> \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3}' \
  --credit-specification CpuCredits=standard \
  --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sensor-seoul}]'
```

- `CpuCredits=standard` — T 계열 unlimited 초과 과금 방지
- `HttpPutResponseHopLimit=1` — 컨테이너(홉 +1)에서 IMDS 토큰을 못 받게. 센서는 IAM 역할도 없음
- 분석 서버는 `t4g.medium`(또는 예산안 C/Supabase 안이면 `t4g.small`), 볼륨 크기는 예산안 따라, `--iam-instance-profile` 로 S3 쓰기 역할
- 센서·분석 서버 모두 **탄력적 IP** 를 붙인다. 중지/시작 때 IP 가 바뀌면 SG·.env·Supabase 허용목록이 다 깨짐. 요금은 자동 할당 공인 IP 와 같음

## 4. 센서 B (버지니아) ★

1. 서울 센서에서 `sudo ./sensor/setup.sh ami-clean`
2. 서울 인스턴스로 AMI 생성 → `aws ec2 copy-image --source-region ap-northeast-2 --region us-east-1 ...`
3. 서울 센서 Cowrie 다시 올리기
4. 버지니아에서 복사 AMI 로 인스턴스 생성, SG 동일하게, Serial Console 비밀번호도 AMI 에 들어 있음
5. 두 센서를 같은 날 노출

## 5. CloudWatch 알람 ★ (알람 10개까지 무료)

```bash
aws cloudwatch put-metric-alarm --region ap-northeast-2 \
  --alarm-name sensor-seoul-cpu --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<i-...> --statistic Average \
  --period 900 --evaluation-periods 1 --threshold 80 --comparison-operator GreaterThanThreshold \
  --alarm-actions <SNS topic ARN>
```

NetworkOut 도 같은 형식. 디스크 사용률은 기본 지표에 없고 CloudWatch Agent 를 깔아야 나온다.
Agent 까지는 안 하고 주간 점검 때 센서에서 `df -h` 를 손으로 본다 (TODO: 4주차에 로그 증가 속도 보고 다시 판단).

## 6. S3 ★

- 버킷 하나 (서울), 퍼블릭 액세스 차단 유지
- 분석 서버 IAM 역할: 이 버킷에만 `s3:PutObject`, `s3:ListBucket`

## 7. Supabase 쪽 (분석 서버가 생긴 뒤)

- Project Settings → API Keys 에서 **서버 전용 secret 키**를 새로 발급해 분석 서버 `.env` 에만 넣는다
- Network Restrictions 는 DB 직접 접속에만 걸리고 API(supabase-py)에는 안 걸리므로 설정할 필요 없음

import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# .env 파일 로드
load_dotenv()


def test_s3_connection():
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    bucket_name = os.getenv("S3_BUCKET")
    region = os.getenv("S3_REGION")

    print(f"--- 설정값 확인 ---")
    print(f"Region: {region}")
    print(f"Bucket: {bucket_name}")
    print(f"Access Key: {access_key}")
    print(f"Secret Key: {secret_key}")

    # 1. Boto3 클라이언트 생성
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        # 2. 버킷 권한 테스트 (가장 간단한 요청)
        print(f"\n--- 연결 테스트 시작 ---")
        s3.head_bucket(Bucket=bucket_name)
        print("✅ 성공: S3 버킷에 정상적으로 접근할 수 있습니다.")

    except ClientError as e:
        print(e.response)
        error_code = e.response['Error']['Code']
        print(f"❌ 실패: {error_code}")
        if error_code == "SignatureDoesNotMatch":
            print("사유: Secret Key가 틀렸거나 서명 방식이 맞지 않습니다. (키를 다시 확인하세요)")
        elif error_code == "403":
            print("사유: 권한이 없습니다. (IAM 정책 확인 필요)")
        elif error_code == "404":
            print("사유: 버킷 이름이 존재하지 않습니다.")
        else:
            print(f"상세 에러: {e}")
    except Exception as e:
        print(f"❌ 기타 에러 발생: {e}")


if __name__ == "__main__":
    test_s3_connection()
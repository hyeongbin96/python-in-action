import csv
import boto3

def apply_tags_to_ec2_instance(instance_id, tags, region):
    ec2_client = boto3.client('ec2', region_name=region)
    ec2_client.create_tags(Resources=[instance_id], Tags=tags)

def delete_tags_from_ec2_instance(instance_id, tags, region):
    ec2_client = boto3.client('ec2', region_name=region)
    ec2_client.delete_tags(Resources=[instance_id], Tags=tags)

def read_csv_and_apply_tags(csv_file_path, region):
    with open(csv_file_path, newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        
        # 헤더를 읽어옵니다.
        header = next(csv_reader)

        for row in csv_reader:
            instance_id = row[0]  # 첫 번째 열에는 인스턴스 ID가 있습니다.

            # 헤더 값에서 태그로 관리할 열의 인덱스
            name_index = header.index("Name")
            rname_index = header.index("Rname")
            se_index = header.index("se")
            task_index = header.index("task")
            newtag_index = header.index("newtag")
            newtag_index = header.index("newtag")

            # 해당 인덱스를 사용하여 태그 키를 선택
            tag_keys = [header[name_index], header[rname_index], header[se_index], header[task_index], header[newtag_index]]

            tag_values = row[5:10]  # "tag1_value", "tag2_value", "tag3_value", "tag4_value" 열

            # 태그 키와 값을 매핑하여 태그를 생성 (value가 공백이 아닌 경우에만)
            tags = [{'Key': key, 'Value': value} for key, value in zip(tag_keys, tag_values) if key and value != "null"]

            # 빈 태그 키를 필터링하고 EC2 인스턴스에 태그를 적용합니다.
            apply_tags_to_ec2_instance(instance_id, tags, region)
            print(f"Tags set for instance: {instance_id}")

            # 기존 태그 가져오기
            ec2 = boto3.resource('ec2', region_name=region)
            instance = ec2.Instance(instance_id)
            existing_tags = instance.tags or []

            # 기존 태그 중에 CSV 파일의 태그와 불일치하는 것 삭제
            tags_to_delete = [tag for tag in existing_tags if tag not in tags]
            if tags_to_delete:
                delete_tags_from_ec2_instance(instance_id, tags_to_delete, region)
                print(f"Tags deleted for instance: {instance_id}")

if __name__ == "__main__":
    # CSV 파일 경로와 AWS 지역(region)을 설정합니다.
    csv_file_path = "/Users/hyeongbin/Github/aws/ec2_tags_management/ec2_tags_out.csv"
    aws_region = "ap-northeast-2"

    # CSV 파일을 읽고 EC2 인스턴스에 태그를 설정합니다.
    read_csv_and_apply_tags(csv_file_path, aws_region)

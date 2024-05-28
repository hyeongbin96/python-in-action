import boto3  # AWS SDK를 사용하기 위한 모듈
import csv  # CSV 파일을 다루기 위한 모듈
import ipaddress  # IP 주소를 다루기 위한 모듈
import argparse  # 명령줄 인자를 처리하기 위한 모듈
import logging  # 로그 출력을 위한 모듈
import sys  # 시스템 관련 기능을 다루는 모듈


# EC2 정보를 저장하는 클래스 정의
class Table(object):
    def __init__(self):
        self._rows = []
        self._instance_id_map = {}
        self._private_ipv4_map = {}
        self._public_ipv4_map = {}

    # 테이블에 행 추가
    def add_row(self, row):
        self._rows.append(row)
        self._instance_id_map[row["Instance_id"]] = row
        self._private_ipv4_map[row["Private_ip"]] = row
        if "Public_ip" in row and row["Public_ip"]:
            self._public_ipv4_map[row["Public_ip"]] = row

    # 모든 행 반환
    def get_rows(self):
        return self._rows

    # 인스턴스 ID로 행 조회
    def get_row_instance_id(self, instance_id):
        return self._instance_id_map.get(instance_id)  # 변경: .get() 메서드 사용

    # 사설 IPv4 주소로 행 조회
    def get_row_private_ipv4(self, ip_address):
        return self._private_ipv4_map.get(ip_address)  # 변경: .get() 메서드 사용

    # 공용 IPv4 주소로 행 조회
    def get_row_public_ipv4(self, ip_address):
        return self._public_ipv4_map.get(ip_address)  # 변경: .get() 메서드 사용

    # 특정 인스턴스 ID 포함 여부 확인
    def contains_instance_id(self, instance_id):
        return instance_id in self._instance_id_map

    # 특정 사설 IPv4 주소 포함 여부 확인
    def contains_private_ipv4(self, ip_address):
        return ip_address in self._private_ipv4_map

    # 특정 공용 IPv4 주소 포함 여부 확인
    def contains_public_ipv4(self, ip_address):
        return ip_address in self._public_ipv4_map


# 로깅 설정
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


# 주어진 IP가 IPv4 주소인지 확인하는 함수
def is_ipv4(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


# 입력 파일 파싱 함수
def parse_input_file(filename):
    with open(filename) as f:
        entries = f.readlines()
    ip_list = []
    instance_list = []
    for entry in entries:
        if is_ipv4(entry.strip()):
            ip_list.append(entry.strip())
        else:
            instance_list.append(entry.strip())
    return ip_list, instance_list


# 태그 리스트를 사전 형태로 변환하는 함수
def dict_format(tag_list):
    tmp_dict = {}
    if not tag_list:
        return tmp_dict
    for tag in tag_list:
        tmp_dict[tag["Key"]] = tag["Value"]
    return tmp_dict


if __name__ == "__main__":
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--inputfile",
        help="한 줄에 하나씩 공용 또는 사설 IPv4 주소 또는 인스턴스 ID가 포함된 입력 파일",
        required=True,
    )
    parser.add_argument("-o", "--outputfile", help="결과가 저장될 CSV 파일", required=True)
    parser.add_argument("-r", "--region", help="인스턴스를 검색할 AWS 리전", required=True)
    parser.add_argument("-p", "--profile", help="기본 자격증명을 사용하지 않을 경우 사용할 자격증명 프로필")
    args = parser.parse_args()
    inputfile = args.inputfile
    outputfile = args.outputfile
    region = args.region
    if args.profile:
        session = boto3.session.Session(region_name=region, profile_name=args.profile)
    else:
        session = boto3.session.Session(region_name=region)

    logging.info("EC2 정보 검색 중...")
    ec2_resource = session.resource("ec2")  # EC2 리소스 생성
    all_instances = ec2_resource.instances.all()  # 모든 EC2 인스턴스 가져오기

    search_ip_list, search_instance_list = parse_input_file(inputfile)

    logging.info("처리 중...")
    all_instance_table = Table()  # 모든 인스턴스 정보를 저장하는 테이블 생성
    private_ipv4_list = []
    public_ipv4_list = []
    for instance in all_instances:
        instance_name = None
        for tag in instance.tags:  # 인스턴스 태그 정보 순회
            if tag["Key"] == "Name":  # 태그 중 'Name' 키 확인
                instance_name = tag["Value"]  # 'Name' 태그의 값을 인스턴스 이름으로 저장
                break
        info_dict = {
            "Instance_id": instance.id,
            "Public_ip": instance.public_ip_address,
            "Private_ip": instance.private_ip_address,
            "hostname": instance_name,  # 인스턴스 이름 저장
            "Instance_state": instance.state["Name"],  # 인스턴스 상태 저장
        }
        info_dict.update(dict_format(instance.tags))  # 태그 정보를 딕셔너리로 변환하여 추가
        all_instance_table.add_row(info_dict)  # 테이블에 행 추가
        private_ipv4_list.append(instance.private_ip_address)
        public_ipv4_list.append(instance.public_ip_address)

    search_table = Table()  # 검색 결과를 저장하는 테이블 생성

    for instance_id in search_instance_list:
        if all_instance_table.contains_instance_id(instance_id):
            search_table.add_row(all_instance_table.get_row_instance_id(instance_id))
    for ip_address in search_ip_list:
        if all_instance_table.contains_private_ipv4(ip_address):
            search_table.add_row(all_instance_table.get_row_private_ipv4(ip_address))
        elif all_instance_table.contains_public_ipv4(ip_address):
            search_table.add_row(all_instance_table.get_row_public_ipv4(ip_address))

    columns = []
    for row in search_table.get_rows():
        for key, value in row.items():
            if key not in columns:
                columns.append(key)
    columns.sort()

    headers = [
        "Instance_id",
        "Public_ip",
        "Private_ip",
        "hostname",
        "Instance_state",
    ]  # 결과 파일 헤더
    
    columns = [e for e in columns if e not in headers]  # 헤더에서 제외할 칼럼 추출
    columns = [
        "Instance_id",
        "Public_ip",
        "Private_ip",
        "hostname",
        "Instance_state",
    ] + columns  # 헤더와 나머지 칼럼 결합

    logging.info("결과를 {}에 저장 중...".format(outputfile))
    with open(outputfile, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(columns)  # CSV 파일 헤더 쓰기
        for row in sorted(
            search_table.get_rows(), key=lambda x: x.get("Instance_state") != "running"
        ):  # 인스턴스 상태에 따라 정렬
            writer.writerow([row.get(column, "null") for column in columns])  # 행 쓰기
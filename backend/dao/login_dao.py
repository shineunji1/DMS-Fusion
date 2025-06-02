import pymysql
from config.mysql import mysql_config
import numpy as np
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility
import time
from model.User import User

class LoginDAO:
    def __init__(self, milvus_host='localhost', milvus_port='19530'):
        self.mysql_config = mysql_config
        self.conn = pymysql.connect(**self.mysql_config)
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collection_name = "user_face_vectors"
        self.collection = None
        
        # Milvus 연결 설정
        self._connect_milvus()
        
    def _close_connection(self):
        """연결 닫기 (필요한 경우)"""
        if self.conn and not self.conn._closed:
            self.conn.close()
            self.conn = None

    def _connect_milvus(self):
        """Milvus 서버에 연결"""
        try:
            if not connections.has_connection("default"):
                connections.connect("default", host=self.milvus_host, port=self.milvus_port)
                print(f"✅ Milvus 연결 성공: {self.milvus_host}:{self.milvus_port}")
                
                if utility.has_collection(self.collection_name):
                    self.collection = Collection(self.collection_name)
                    self.collection.load()
                    print(f"✅ 얼굴 벡터 컬렉션 로드 완료: {self.collection_name}")
                else:
                    fields = [
                            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128),
                            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),  # 실제 사용자 ID
                            FieldSchema(name="direction", dtype=DataType.VARCHAR, max_length=10),  # 방향(front, left, right)
                            FieldSchema(name="timestamp", dtype=DataType.INT64)
                    ]
                    
                    schema = CollectionSchema(fields, description="Face vectors with direction")
                    collection = Collection(self.collection_name, schema)

                    index_params = {"metric_type": "L2", "index_type": "HNSW", "params": {"M": 32, "efConstruction": 400}}
                    collection.create_index(field_name="vector", index_params=index_params)
                    print(f"✅ Milvus 컬렉션 생성 및 인덱스 생성 완료: {self.collection_name}")

            else:
                # 이미 연결되어 있는 경우
                if utility.has_collection(self.collection_name):
                    self.collection = Collection(self.collection_name)
                    print(f"✅ 얼굴 벡터 컬렉션 로드 완료: {self.collection_name}")       
                else:
                    collection = Collection(self.collection_name)
                    print(f"✅ 기존 Milvus 컬렉션 로드 완료: {self.collection_name}")
        
        except Exception as e:
            print(f"❌ Milvus 연결 실패: {e}")
            
    def get_last_user_id(self):
        """Milvus에서 마지막으로 등록된 사용자 ID를 가져옵니다."""
        try:
            # 벡터 컬렉션 가져오기
            collection = self.get_face_collection()
            
            # 2. 자동 생성된 ID를 기준으로 가져오는 경우
            res = collection.query(
                expr="id != 0",
                output_fields=["user_id","id","timestamp"],
            )
            
            print("응답:" , res)
            
            if res and len(res) > 0:
                print("조회된 id: ", res[-1]["user_id"])
                return res[-1]["user_id"]  # 마지막 user_id 반환
            else:
                return None  # 데이터가 없는 경우
                
        except Exception as e:
            print(f"❌ Milvus에서 마지막 사용자 ID 조회 실패: {e}")
            return None

    def get_face_collection(self):
        """얼굴 벡터 컬렉션 객체 반환"""
        if self.collection is None:
            self._connect_milvus()  # 연결 재시도
        return self.collection
    
    def find_face_by_vector(self, query_vector, threshold=0.05, top_k=5):
        """
        얼굴 벡터를 이용해 사용자 검색
        
        Args:
            query_vector (numpy.ndarray or list): 검색할 얼굴 벡터
            threshold (float): 일치 판정 임계값 (기본값: 0.4)
            top_k (int): 검색할 최대 결과 수
            
        Returns:
            str or None: 일치하는 사용자 ID 또는 None
        """
        try:
            collection = self.get_face_collection()
            if collection is None:
                print("❌ Milvus 컬렉션에 접근할 수 없습니다.")
                return None
            
            # 검색 파라미터 설정
            search_params = {"metric_type": "L2", "params": {"ef": 300}}
            
            # 벡터를 리스트로 변환 (Milvus 요구사항)
            query_vector_list = query_vector.tolist() if not isinstance(query_vector, list) else query_vector
            
            # 유사 벡터 검색 수행
            search_result = collection.search(
                data=[query_vector_list],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["user_id","timestamp"]
            )
            
            print("조회결과:",search_result)
            
            # 검색 결과 처리
            best_match = None

            for hits in search_result:
                for hit in hits:
                    distance = hit.distance
                    
                    print(f"비교 거리: {distance:.4f} (ID: {hit.id}) (일치 값: {threshold})")
                    
                    if distance < threshold:
                        if best_match is None or distance < best_match["distance"]:
                            best_match = {
                                "user_id": str(hit.user_id),  # Milvus ID를 user_id로 사용
                                "distance": distance,
                                "id": hit.id
                            }
            
            if best_match:
                user_id = best_match["user_id"]
                print(f"✅ 얼굴 인증 성공! 사용자 ID: {user_id}, 거리: {best_match['distance']:.4f}")
                
                return user_id
            
            print("❌ 일치하는 얼굴 벡터 없음")
            return None
            
        except Exception as e:
            print(f"❌ 얼굴 인증 중 오류 발생: {e}")
            return None
    
    # LoginDAO.py 수정 - 데이터 삽입을 위한 메서드 추가
    def insert_face_vector(self, user_id, face_vector, direction):
        """
        얼굴 벡터를 Milvus에 저장
        
        Args:
            user_id (str): 사용자 ID
            face_vector (numpy.ndarray): 얼굴 벡터
            direction (str): 얼굴 방향 (front, left, right)
        """
        try:
            collection = self.get_face_collection()
            if collection is None:
                print("❌ Milvus 컬렉션에 접근할 수 없습니다.")
                return False
            
            # 현재 타임스탬프
            timestamp = int(time.time())
            
            # 벡터를 리스트로 변환 (Milvus 요구사항)
            vector_list = face_vector.tolist() if not isinstance(face_vector, list) else face_vector
            
            # 삽입할 데이터 준비
            data = [
                [vector_list],   # vector 필드
                [str(user_id)],  # user_id 필드 (문자열로 변환)
                [direction],     # direction 필드
                [timestamp]      # timestamp 필드
            ]
            
            # Milvus에 데이터 삽입
            result = collection.insert(data)
            print("결과:",result)
            print(f"✅ 얼굴 벡터 삽입 완료 - user_id: {user_id}, direction: {direction}")
            return True
            
        except Exception as e:
            print(f"❌ Milvus 데이터 삽입 중 오류 발생: {e}")
            return False

    # 트랜잭션을 위한 컨텍스트 매니저 제공
    def transaction(self): 
        return self.conn.cursor()
    
    def register_user(self, user_id):
        # 매번 새로운 연결 생성
        conn = pymysql.connect(**self.mysql_config)
        try:
            with conn.cursor() as cursor:
                # INSERT IGNORE 사용하여 중복 키 회피
                sql = "INSERT IGNORE INTO moca_user(user_num,signup_date) VALUES (%s,NOW())"
                result = cursor.execute(sql, (user_id))
                
                # 영향받은 행이 있거나, 이미 존재하는 경우 모두 성공으로 처리
                conn.commit()
                
                # 실제로 삽입되었는지 확인
                check_sql = "SELECT 1 FROM moca_user WHERE user_num = %s"
                cursor.execute(check_sql, (user_id))
                exists = cursor.fetchone() is not None
                
                if exists:
                    print(f"✅ 유저 ID {user_id} 확인 완료!")
                    return True
                else:
                    print(f"❌ 유저 ID {user_id} 확인 실패!")
                    return False
                    
        except Exception as e:
            print(f"❌ 유저 등록 확인 중 오류 발생: {e}")
            try:
                conn.rollback()
            except:
                pass
            return False
        finally:
            conn.close()  # 항상 연결 닫기
    
    # 얼굴 벡터  터미널 출력
    def save_face_vector(self, user_id, face_vector):
        print(f"✅ 얼굴 벡터 저장 (user_id={user_id}): {face_vector}")
        
    def profile_add(self,item):
        conn = pymysql.connect(**self.mysql_config)
        try: 
            conn.autocommit(False)
            
            with conn.cursor() as cursor:
                insert_sql1 = """UPDATE moca_user
                                SET user_name = %s, user_pw = %s
                                WHERE user_num = %s
                            """
                insert_sql2 = """
                        INSERT INTO moca_profile (user_num, profile_name, profile_color)
                        VALUES (%s, %s, %s)
                """
                
                cursor.execute(insert_sql1,(item.user_name, item.user_pwd,item.user_id))
                cursor.execute(insert_sql2,(item.user_id,item.profile_name, item.profile_color))
                
                conn.commit()
                print("트랜잭션이 성공적으로 커밋되었습니다.")
                
                return True
            
        except Exception as e:
            conn.rollback()
            print("오류발생 :", e)
            print("작업이 롤백 되었습니다")
            return False
        
        finally:
            conn.close()
    
    def find_user(self, user_id):
        conn = pymysql.connect(**self.mysql_config)
        try:
            with conn.cursor() as cursor :
                sql = """
                    select 
                    moca_user.user_num,moca_user.user_name, moca_profile.profile_name, moca_profile.profile_color, moca_user.signup_date 
                    from moca_user join moca_profile on moca_user.user_num = moca_profile.user_num where moca_user.user_num = %s;
                """
                
                cursor.execute(sql, (user_id))
                
                result = cursor.fetchone()
                user_data = User.from_tuple(result).dict()
                print("dao조회결과:",result)
                print("dict화:",user_data)
                if(result) :
                    return user_data
                else :
                    return False
                
            
        except Exception as e:
            conn.rollback()
            print("조회 오류 발생!:",e)
            print("작업을 롤백 합니다!")
            return False
        finally:
            conn.close()

    def manual_login(self, user_pwd):
        conn = pymysql.connect(**self.mysql_config)
        try:
            with conn.cursor() as cursor :
                sql = """
                    select 
                    moca_user.user_num,moca_user.user_name, moca_profile.profile_name, moca_profile.profile_color, moca_user.signup_date 
                    from moca_user join moca_profile on moca_user.user_num = moca_profile.user_num where moca_user.user_pw = %s;
                """
                
                cursor.execute(sql, (user_pwd))
                
                result = cursor.fetchone()
                user_data = User.from_tuple(result).dict()
                print("dao조회결과:",result)
                print("dict화:",user_data)
                if(result) :
                    return user_data
                else :
                    return False
                
            
        except Exception as e:
            conn.rollback()
            print("조회 오류 발생!:",e)
            print("작업을 롤백 합니다!")
            return False
        finally:
            conn.close()
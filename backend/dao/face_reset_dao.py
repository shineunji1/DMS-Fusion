import pymysql
from config.mysql import mysql_config
from pymilvus import connections, Collection
import os
import cv2

class FaceResetDAO:
    def __init__(self):
        self.conn = pymysql.connect(**mysql_config)

    # 트랜잭션을 위한 컨텍스트 매니저 제공
    def transaction(self): 
        return self.conn.cursor()
    
    # MySQL에서 user_id에 해당하는 user_num 조회
    def get_user_by_id(self, user_id): 
        conn = self.conn
        try:
            with conn.cursor() as cursor:
                sql = "SELECT user_num FROM moca_profile WHERE profile_num = %s"
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                return result["user_num"] if result else None
        finally:
            conn.close()
    
    # 얼굴 벡터  터미널 출력
    def save_face_vector(self, user_id, face_vector):
        print(f"✅ 얼굴 벡터 저장 (user_id={user_id}): {face_vector}")
        
import cv2
import dlib
import numpy as np
import time
import datetime
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility

# ✅ Milvus 연결 설정
milvus_host = 'localhost'
milvus_port = '19530'

if not connections.has_connection("default"):
    try:
        connections.connect("default", host=milvus_host, port=milvus_port)
        print(f"✅ Milvus 연결 성공: {milvus_host}:{milvus_port}")
        version = utility.get_server_version()
        print(f"Milvus Version: {version}")
    except Exception as e:
        print(f"❌ Milvus 연결 실패: {e}")
        exit()

# ✅ dlib 벡터용 컬렉션 설정
collection_name = "realtime_face_vectors"

if not utility.has_collection(collection_name):
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128),  # dlib 벡터는 128차원
        FieldSchema(name="timestamp", dtype=DataType.INT64)  # 저장 시간 기록
    ]
    schema = CollectionSchema(fields, description="Realtime dlib face vectors collection")
    collection = Collection(collection_name, schema)

    index_params = {"metric_type": "L2", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}}
    collection.create_index(field_name="vector", index_params=index_params)
    print(f"✅ Milvus 컬렉션 생성 및 인덱스 생성 완료: {collection_name}")
else:
    collection = Collection(collection_name)
    print(f"✅ 기존 Milvus 컬렉션 로드 완료: {collection_name}")

# ✅ 컬렉션 로드
try:
    collection.load()
    print("✅ Milvus 컬렉션이 성공적으로 로드되었습니다.")
except Exception as e:
    print(f"❌ Milvus 컬렉션 로드 실패: {e}")

# ✅ dlib 얼굴 인식기 및 특징 추출기 초기화
detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor("../models/shape_predictor_68_face_landmarks.dat")
face_rec_model = dlib.face_recognition_model_v1("../models/dlib_face_recognition_resnet_model_v1.dat")
print("✅ dlib 얼굴 인식기 및 특징 추출기 초기화 완료")

# 얼굴 벡터 추출 및 저장 함수
def extract_and_save_face_vector(frame, face):
    try:
        # 얼굴 랜드마크 감지
        shape = sp(frame, face)
        
        # 얼굴 특징 벡터 계산
        face_descriptor = face_rec_model.compute_face_descriptor(frame, shape)
        
        # 128차원 벡터로 변환
        dlib_vector = np.array(face_descriptor).tolist()
        
        # 현재 타임스탬프
        current_timestamp = int(time.time())
        
        # Milvus에 저장
        insert_data = [
            [dlib_vector],  # vector 필드
            [current_timestamp]  # timestamp 필드
        ]
        
        insert_result = collection.insert(insert_data)
        
        # 벡터 저장 정보 출력
        face_id = insert_result.primary_keys[0]
        print(f"✅ 얼굴 벡터 저장 완료! ID: {face_id}, 시간: {datetime.datetime.fromtimestamp(current_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True, face_id, dlib_vector
    except Exception as e:
        print(f"❌ 얼굴 벡터 추출 또는 저장 실패: {e}")
        return False, None, None

# 비슷한 얼굴 검색 함수
def search_similar_faces(vector, top_k=5):
    try:
        search_params = {"metric_type": "L2", "params": {"ef": 100}}
        search_result = collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["timestamp"]
        )
        
        results = []
        for hits in search_result:
            for hit in hits:
                # 저장 시간을 읽기 쉬운 형식으로 변환
                timestamp = hit.entity.get('timestamp')
                datetime_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                results.append({
                    "id": hit.id,
                    "timestamp": timestamp,
                    "datetime": datetime_str,
                    "distance": hit.distance
                })
        
        return results
    except Exception as e:
        print(f"❌ 유사 얼굴 검색 실패: {e}")
        return []

# 데이터베이스 조회 함수
def query_face_vectors(limit=10):
    try:
        query_result = collection.query(
            expr="id >= 0",
            output_fields=["id", "timestamp"],
            limit=limit,
            sort="timestamp desc"  # 최신순 정렬
        )
        
        results = []
        for item in query_result:
            timestamp = item['timestamp']
            datetime_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            results.append({
                "id": item['id'],
                "timestamp": timestamp,
                "datetime": datetime_str
            })
        
        return results
    except Exception as e:
        print(f"❌ 벡터 조회 실패: {e}")
        return []

# 데이터베이스에 저장된 얼굴 벡터 수 조회
def count_saved_faces():
    try:
        count = collection.num_entities
        return count
    except Exception as e:
        print(f"❌ 저장된 얼굴 수 조회 실패: {e}")
        return 0

# 실시간 웹캠 얼굴 탐지 및 벡터 저장 (수동 저장만 가능)
def realtime_face_detection():
    # 웹캠 초기화
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return
    
    # 최근 저장된 벡터 정보
    last_saved_id = None
    last_saved_vector = None
    
    # 유사 얼굴 검색 결과
    similar_faces = []
    
    print("🎥 실시간 얼굴 감지 시작...")
    print("✓ 's' 키를 누르면 현재 얼굴 벡터를 저장합니다.")
    print("✓ 'f' 키를 누르면 현재 얼굴과 유사한 얼굴을 검색합니다.")
    print("✓ 'q' 키를 누르면 종료됩니다.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임을 읽을 수 없습니다.")
            break
        
        # 화면 좌우 반전 (거울 효과)
        frame = cv2.flip(frame, 1)
        
        # 디스플레이용 프레임 복사
        display_frame = frame.copy()
        
        # RGB 변환 (dlib용)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 얼굴 감지
        faces = detector(rgb_frame)
        
        # 감지된 얼굴 표시 및 처리
        current_face = None
        
        for i, face in enumerate(faces):
            # 현재 처리 중인 얼굴 설정 (첫 번째 얼굴을 기본으로 선택)
            if i == 0:
                current_face = face
            
            # 얼굴 주위에 사각형 그리기
            x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 텍스트 배경 그리기
            cv2.rectangle(display_frame, (x1, y1-30), (x1 + 120, y1), (0, 255, 0), -1)
            cv2.putText(display_frame, f"Face #{i+1}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 유사 얼굴 검색 결과 표시
        if similar_faces:
            y_pos = 70
            cv2.putText(display_frame, "Similar Faces:", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            y_pos += 30
            
            for idx, face in enumerate(similar_faces[:3]):  # 상위 3개만 표시
                cv2.putText(display_frame, f"#{idx+1} ID: {face['id']} ({face['datetime']})", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
                y_pos += 25
                cv2.putText(display_frame, f"    Distance: {face['distance']:.4f}", 
                           (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
                y_pos += 30
        
        # 지침 표시
        cv2.putText(display_frame, "s: Save  f: Find similar  q: Quit", 
                   (10, display_frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(display_frame, f"Faces: {len(faces)}", 
                   (display_frame.shape[1]-150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # 마지막 저장 ID 표시
        if last_saved_id:
            cv2.putText(display_frame, f"Last Saved ID: {last_saved_id}", 
                       (display_frame.shape[1]-220, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 프레임 표시
        cv2.imshow("Face Detection & Manual Save", display_frame)
        
        # 키 입력 처리
        key = cv2.waitKey(1) & 0xFF
        
        # 's' 키: 현재 얼굴 수동 저장
        if key == ord('s') and current_face is not None:
            print("현재 얼굴 수동 저장 중...")
            success, face_id, vector = extract_and_save_face_vector(rgb_frame, current_face)
            if success:
                last_saved_id = face_id
                last_saved_vector = vector
                print(f"✅ 얼굴 수동 저장 성공! ID: {face_id}")
        
        # 'f' 키: 유사 얼굴 검색
        elif key == ord('f') and last_saved_vector is not None:
            print(f"ID {last_saved_id}와 유사한 얼굴 검색 중...")
            similar_faces = search_similar_faces(last_saved_vector, top_k=5)
            
            print("\n✅ 유사 얼굴 검색 결과:")
            for idx, face in enumerate(similar_faces):
                print(f"#{idx+1} ID: {face['id']}, 날짜: {face['datetime']}, 거리: {face['distance']:.6f}")
        
        # 'q' 키: 종료
        elif key == ord('q'):
            break
    
    # 자원 해제
    cap.release()
    cv2.destroyAllWindows()

def realtime_face_detection_with_auto_recognition():
    # 웹캠 초기화
    cap = cv2.VideoCapture(0)
    frame_counter = 0
    process_every_n_frames = 10  # 5프레임마다 한 번만 인식 처리
    
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return
    
    # 데이터베이스에서 모든 얼굴 벡터 미리 로드
    print("데이터베이스에서 얼굴 벡터 로드 중...")
    try:
        # 전체 얼굴 벡터 조회 (최대 100개)
        all_vectors = collection.query(
            expr="id >= 0",
            output_fields=["id", "vector", "timestamp"],
            limit=100
        )
        print(f"✅ {len(all_vectors)}개의 얼굴 벡터를 로드했습니다.")
    except Exception as e:
        print(f"❌ 얼굴 벡터 로드 실패: {e}")
        all_vectors = []
    
    print("🎥 실시간 얼굴 감지 및 자동 인식 시작...")
    print("✓ 's' 키를 누르면 현재 얼굴 벡터를 저장합니다.")
    print("✓ 'q' 키를 누르면 종료됩니다.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임을 읽을 수 없습니다.")
            break
        
        # 화면 좌우 반전 (거울 효과)
        frame = cv2.flip(frame, 1)
        
        # 디스플레이용 프레임 복사
        display_frame = frame.copy()
        
        # 얼굴 인식은 n프레임마다 한 번만 수행
        if frame_counter % process_every_n_frames == 0:
            # RGB 변환 (dlib용)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 얼굴 감지
            faces = detector(rgb_frame)
            
            # 감지된 얼굴 표시 및 처리
            for i, face in enumerate(faces):
                # 얼굴 주위에 사각형 그리기
                x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # 텍스트 배경 그리기
                cv2.rectangle(display_frame, (x1, y1-30), (x1 + 120, y1), (0, 255, 0), -1)
                cv2.putText(display_frame, f"Face #{i+1}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # 얼굴 벡터 추출 (저장하지 않고 임시 사용)
                try:
                    # 얼굴 랜드마크 감지
                    shape = sp(rgb_frame, face)
                    
                    # 얼굴 특징 벡터 계산
                    face_descriptor = face_rec_model.compute_face_descriptor(rgb_frame, shape)
                    
                    # 128차원 벡터로 변환
                    current_vector = np.array(face_descriptor).tolist()
                    
                    # 데이터베이스의 모든 벡터와 비교
                    best_match = None
                    best_distance = 0.6  # 임계값 (이 값보다 작으면 동일인물로 판단)
                    
                    for stored_face in all_vectors:
                        stored_vector = stored_face['vector']
                        stored_id = stored_face['id']
                        timestamp = stored_face['timestamp']
                        date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 유클리드 거리 계산 (L2 거리)
                        distance = np.linalg.norm(np.array(current_vector) - np.array(stored_vector))
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_match = {"id": stored_id, "distance": distance, "datetime": date_str}
                    
                    # 매치 결과 표시
                    if best_match:
                        match_text = f"ID: {best_match['id']}"
                        cv2.putText(display_frame, match_text, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        cv2.putText(display_frame, f"Dist: {best_match['distance']:.4f}", (x1, y2 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    else:
                        cv2.putText(display_frame, "Unknown", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                except Exception as e:
                    print(f"❌ 얼굴 벡터 처리 오류: {e}")
            
            # 지침 표시
            cv2.putText(display_frame, "s: Save  q: Quit", 
                    (10, display_frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(display_frame, f"Faces: {len(faces)}", 
                    (display_frame.shape[1]-150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            # 프레임 표시
            cv2.imshow("Face Recognition - Auto Detection", display_frame)
        
        frame_counter += 1
        
        # 키 입력 처리
        key = cv2.waitKey(1) & 0xFF
        
        # 's' 키: 현재 얼굴 수동 저장
        if key == ord('s') and len(faces) > 0:
            face = faces[0]  # 첫 번째 얼굴 선택
            success, face_id, vector = extract_and_save_face_vector(rgb_frame, face)
            if success:
                print(f"✅ 얼굴 수동 저장 성공! ID: {face_id}")
                # 새로 저장된
                all_vectors.append({"id": face_id, "vector": vector, "timestamp": int(time.time())})
        
        # 'q' 키: 종료
        elif key == ord('q'):
            break
    
    # 자원 해제
    cap.release()
    cv2.destroyAllWindows()

# 모든 저장된 얼굴 벡터 조회 및 출력
def view_all_face_vectors(limit=20):
    print(f"\n최근 저장된 얼굴 벡터 조회 (최대 {limit}개):")
    print("-" * 60)
    
    faces = query_face_vectors(limit)
    
    if not faces:
        print("저장된 얼굴 벡터가 없습니다.")
        return
    
    for idx, face in enumerate(faces):
        print(f"#{idx+1} ID: {face['id']}, 저장 시간: {face['datetime']}")
    
    print("-" * 60)
    print(f"총 {len(faces)}개의 얼굴 벡터가 조회되었습니다.")
    print(f"전체 저장된 얼굴 벡터 수: {count_saved_faces()}")

# 특정 ID의 얼굴 벡터로 유사 얼굴 검색
def find_similar_by_id(face_id, top_k=5):
    try:
        # 지정한 ID의 벡터 조회
        vector_result = collection.query(
            expr=f"id == {face_id}",
            output_fields=["vector", "timestamp"]
        )
        
        if not vector_result:
            print(f"❌ ID {face_id}에 해당하는 얼굴 벡터를 찾을 수 없습니다.")
            return
        
        vector = vector_result[0]['vector']
        timestamp = vector_result[0]['timestamp']
        date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n🔍 ID {face_id} 얼굴 벡터 (저장 시간: {date_str})로 유사 얼굴 검색:")
        print("-" * 60)
        
        # 유사 얼굴 검색
        similar_faces = search_similar_faces(vector, top_k)
        
        if not similar_faces:
            print("유사한 얼굴을 찾을 수 없습니다.")
            return
        
        for idx, face in enumerate(similar_faces):
            print(f"#{idx+1} ID: {face['id']}, 날짜: {face['datetime']}, 거리: {face['distance']:.6f}")
        
        print("-" * 60)
    
    except Exception as e:
        print(f"❌ ID로 유사 얼굴 검색 실패: {e}")

# 메인 함수
def main():
    while True:
        print("\n얼굴 인식 및 벡터 저장/조회 시스템")
        print("=" * 40)
        print("1. 실시간 얼굴 감지 및 벡터 저장")
        print("2. 저장된 얼굴 벡터 조회")
        print("3. ID로 유사 얼굴 검색")
        print("4. 저장된 얼굴 수 확인")
        print("5. 실시간 얼굴 감지 및 자동 인식")  # 새 옵션 추가
        print("0. 종료")
        print("=" * 40)
        
        choice = input("선택하세요 (0-5): ")
        
        if choice == '1':
            # 실시간 얼굴 감지 및 벡터 저장
            realtime_face_detection()
        
        elif choice == '2':
            # 저장된 얼굴 벡터 조회
            limit = input("조회할 최대 개수 (기본: 20): ")
            try:
                limit = int(limit) if limit else 20
                view_all_face_vectors(limit)
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
        
        elif choice == '3':
            # ID로 유사 얼굴 검색
            face_id = input("검색할 얼굴 ID: ")
            try:
                face_id = int(face_id)
                top_k = input("검색할 유사 얼굴 수 (기본: 5): ")
                top_k = int(top_k) if top_k else 5
                find_similar_by_id(face_id, top_k)
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
        
        elif choice == '4':
            # 저장된 얼굴 수 확인
            count = count_saved_faces()
            print(f"\n현재 데이터베이스에 저장된 얼굴 벡터 수: {count}")
            
                
        elif choice == '5':
            # 실시간 얼굴 감지 및 자동 인식
            realtime_face_detection_with_auto_recognition()
        
        elif choice == '0':
            # 종료

            print("프로그램을 종료합니다.")
            break
        
        else:
            print("❌ 올바른 선택이 아닙니다. 다시 시도해주세요.")

# 프로그램 실행
if __name__ == "__main__":
    main()
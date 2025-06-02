class SeatDAO:
    def __init__(self):
        self.seat_data = {"position": "머리", "angle": 0, "좌우": 0.2, "상하": -1.0, "전후": 0.0}

    def get_seat_settings(self):
        return self.seat_data

    def save_seat_settings(self, settings):
        self.seat_data = settings.dict()
        return {"message": "Seat settings updated successfully", "data": self.seat_data}

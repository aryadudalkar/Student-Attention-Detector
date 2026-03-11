from collections import deque

class SequenceBuffer:
    def __init__(self, maxlen=50):
        self.maxlen = maxlen
        self.buffers = {}

    def add(self, student_id, feature_vector):
        if student_id not in self.buffers:
            self.buffers[student_id] = deque(maxlen=self.maxlen)

        self.buffers[student_id].append(feature_vector)

    def get_sequence(self, student_id):
        if student_id in self.buffers and len(self.buffers[student_id]) == self.maxlen:
            return list(self.buffers[student_id])
        return None
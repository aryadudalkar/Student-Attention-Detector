import numpy as np

class SimpleTracker:
    def __init__(self):
        self.next_id = 0
        self.objects = {}

    def update(self, boxes):

        updated_objects = {}

        for box in boxes:
            x1, y1, x2, y2 = box
            center = ((x1+x2)//2, (y1+y2)//2)

            assigned = False

            for obj_id, prev_center in self.objects.items():
                dist = np.linalg.norm(np.array(center) - np.array(prev_center))

                if dist < 50:
                    updated_objects[obj_id] = center
                    assigned = True
                    break

            if not assigned:
                updated_objects[self.next_id] = center
                self.next_id += 1

        self.objects = updated_objects
        return self.objects
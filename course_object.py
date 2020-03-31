class Course():

    def __init__(self, name, courseID):
        self.name = name
        self.courseID = courseID
        self.assignments = []

    def get_assignments(self):
        return self.assignments

    def get_name(self):
        return self.name

    def get_id(self):
        return self.courseID

    def add_assignment(self,new_assignment):
        self.assignments.append(new_assignment)

    def remove_assignment(self, assignment):
        if assignment in self.assignments:
            self.assignments.remove(assignment)

    



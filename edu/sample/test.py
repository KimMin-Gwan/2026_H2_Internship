
class Sample():
    def __init__(self):
        self.data = "샢믈"
        
    def get_data(self):
        return self.data
    
    def set_data(self, data):
        self.data = data
        return
    
    
    
sample = Sample()
sample2 = Sample()
print(sample)
print(sample2)
print(sample.get_data())
sample.set_data(data="샘플")
print(sample.get_data())
print(sample2.get_data())




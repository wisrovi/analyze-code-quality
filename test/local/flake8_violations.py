def calculate_area(length,width):#missing spaces and type hints
    return length*width  #no spaces around operator

def process_data(data): #missing type hints
    result={}
    for item in data:
        if item in result:
            result[item]+=1
        else:
            result[item]=1
    return result

def main():
    area=calculate_area(5,10)  #no spaces around operator
    print(f"Area: {area}")
    
    data=[1,2,2,3,3,3]  #no spaces after commas
    processed=process_data(data)
    print(f"Processed: {processed}")

if __name__=="__main__":  #no spaces around operator
    main()
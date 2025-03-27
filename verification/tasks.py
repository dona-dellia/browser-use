"""Module to measure the progress of US enrichment."""

from os import listdir
from os.path import isfile, join
import json


CONVERSATION_PATH = '../verification/US/'
LEN_EXPLANATION = 200

def get_steps_of_tasks(type, us_id):
    """
    Get all steps did for the browser
    user to execute US-id

    Args:
    -----
       - type: the US type if [raw|E1|E2]
       - us_id: the US number [1..10]

    Returns:
    --------
        - a list of all files where each file refer a browser user step
    """
    path = str(us_id) +"/"+type+'/log'
    final_path = CONVERSATION_PATH+path

    logs = [final_path+"/"+f for f in listdir(final_path) if isfile(join(final_path, f))]
    # "evaluation_previous_goal" in first file is always Unknown
    logs = logs[1:]
    return logs

def evalate_efficient_amount_steps(us_id, type):
    """
    """
    #Aqui é importante saber se cumpriu a tarefa?

    test_case_steps = count_tastcase_step(us_id)
    logs = get_steps_of_tasks(type, us_id)

    efficiency = test_case_steps/len(logs)
    print(round(efficiency,2))


def count_tastcase_step(us_id):
    """
    """
    path = CONVERSATION_PATH+str(us_id)+"/testcase/testcase.json"
    with open(path, 'r', encoding="utf-8") as file:
        content = file.read()
        json_file = json.loads(content)
    
    return(len(json_file["description"]))

def evaluate_US_perform():
    """
    """
    pass

def evaluate_task_perfom(us_id, type):
    """
    Evaluate the amount of success obteined
    per amount of steps did.

    Args:
    -----
        - type: the US type if [raw|E1|E2]
        - us_id: the US number [1..10]

    Returns:
    --------
        - A dict with:
            - STEPs: amount of steps did
            - sucess: amount of success got
            - precision: proportion of success/STEPs
            - tasks_to_be_improved: list of files when the browser user fail
    """
    logs = get_steps_of_tasks(type, us_id)

    tasks_to_be_improved = []
    STEPS = len(logs)
    success = 0

    for log in logs:

        with open(log, 'r', encoding="utf-8") as file:
            for line in file.readlines():
                # There are 2 lines with evaluation previous goals the
                # first one it is an explanation about the attribute has 147 characters.
                if "evaluation_previous_goal" in line and len(line) < LEN_EXPLANATION:
                    if "Success" in line:
                        success +=1
                    else:
                        tasks_to_be_improved.append(log)
    try:
        validation = success/STEPS
    except ZeroDivisionError:
        validation = '-'

    return {"STEPS": STEPS,
            "success":success,
            "precision": validation,
            "tasks_to_be_improved":tasks_to_be_improved}

def print_evaluate_task(**kwords):
    """
    Structureted print using a result of
    ``evaluate_task_perfom(..)``

    """
    print("----------------------------")
    print("Steps: ", kwords["STEPS"])
    print("Success: ", kwords["success"])
    validation = kwords["success"]/kwords["STEPS"]
    print("----------------------------")
    print(f"Precision: {validation:.2f}")
    print("----------------------------")
    print("Tasks to be improved:")

    for task in kwords["tasks_to_be_improved"]:
        print("\t - ", task)

if __name__ == '__main__':
    #test

    #precision = evaluate_task_perfom(us_id, "E1")
    #print_evaluate_task(**precision)
    evalate_efficient_amount_steps(1, "raw")
 
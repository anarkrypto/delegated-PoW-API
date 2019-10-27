from flask import Flask, jsonify, request
from functions import block_create, balance, frontier, broadcast, worker_account, min_fee, max_multiplier, use_active_difficulty, get_difficulty, solve_work, service_port, get_my_ip, worker_private_key, worker_representative, general_account, sign_new_account_code, sign_new_ip_code, pending_filter, receive, check_history, register, encode_ip, check_key_pair, node
from nanolib import Block
import requests
import json
import waitress

app = Flask(__name__)

#Check inputs
if check_key_pair(worker_account, worker_private_key) is False:
    print ("Invalid key pair")
    quit()
#...
print ("Configurations okay")

#Check if node is online
try:
    r = requests.post(node, json={"action": "version"})
except:
    print ("Node " + node + " Offline! Exiting")
    quit()
else:
    if 'node_vendor' in r.json():
        print ("Node (" + r.json()["node_vendor"] + ") is online on " + node)
    else:
        print ("Node " + node + " error! Exiting")
        quit()

#Registration Process
print ("Checking register")
history = check_history(worker_account, general_account)
if history is not None:
    if int(history["amount"]) == sign_new_account_code:
        print ("Found your worker account registration: " + worker_account)
        myIP = get_my_ip() #check IP register
        ip_account = encode_ip(myIP)
        history = check_history(worker_account, ip_account)
        if history is not None:
            print ("Found your actuall IP address registration: " + myIP)
            if int(history["amount"]) != sign_new_ip_code:
                print ("Incorrect amount in your IP address register")
                register (worker_account, worker_representative, frontier(worker_account), ip_account, sign_new_ip_code, 1.0)
        else:
            print ("Not found your actuall IP address registration: " + myIP)
            register (worker_account, worker_representative, frontier(worker_account), ip_account, sign_new_ip_code, 1.0)
    else:
        print ("Incorrect amount in register")
        register (worker_account, worker_representative, frontier(worker_account), general_account, sign_new_account_code, 1.0)
else:
    print ("Not found your worker registration: " + worker_account)
    register (worker_account, worker_representative, frontier(worker_account), general_account, sign_new_account_code, 1.0)


#convert to raws
fee = int(min_fee * 1000000000000000000000000000000)

@app.route('/open_request', methods=['GET', 'POST'])
def opening_request():
    print ("Open Request")
    header = {"version": "0.0.1", "reward_account": worker_account, "fee": fee, "max_multiplier": max_multiplier}
    if use_active_difficulty == True:
        header["min_multiplier"] = get_difficulty()
    else:
        header["min_multiplier"] = 1.0
    return header


@app.route('/request_work', methods=['GET', 'POST'])
def request_work():
    #request transactions
    data = request.get_json()
    global fee

    #check if user and worker transaction are present
    if "user_transaction" in data:
        user = data.get("user_transaction")
    else:
        print ("User transaction missing")
        return {"Error": "User transaction missing"}

    if "worker_transaction" in data:
        worker = data.get("worker_transaction")
    else:
        print ("Worker transaction missing")
        return {"Error": "Worker transaction missing"}


    #Read transaction and check if is valid
    user_block = block_create(user.get('block_type'), user.get('account').replace("xrb_", "nano_"), user.get('representative'), user.get('previous'), user.get("link_as_account"), int(user.get('balance')), user.get("signature"))
    if user_block == "invalid":
        print ("Invalid user transaction")
        return '{"Error": "Invalid user transaction"}'
    worker_block = block_create(worker.get('block_type'), worker.get('account').replace("xrb_", "nano_"), worker.get('representative'), worker.get('previous'), worker.get("link_as_account"), int(worker.get('balance')), worker.get("signature"))
    if worker_block == "invalid":
        print ("Invalid worker transaction")
        return {"Error": "Invalid worker transaction"}

    #If account source in both transactions is different
    if user_block.account != worker_block.account :
        print ("Different source accounts ")
        return '{"Error": "Different Accounts source"}'

    #If worker account is wrong
    if worker_block.link_as_account != worker_account:
        print("Worker account is incorrect")
        return {"Error": "Worker account is incorrect"}

    #Check if previous block in worker hash is correct
    if worker_block.previous != user_block.block_hash:
        print ("Incorrect previous block in worker block")
        return {"Error": "Incorrect previous block in worker block" }

    #Recalculate the Fee with active_difficulty with 10% tolerance
    if use_active_difficulty == True:
        multiplier = get_difficulty()
        if (multiplier > max_multiplier):
            return {"Error": "Maximum difficulty exceded"}
        else:
            print ("Using active difficulty: " + str(multiplier))
        if multiplier * 0.9 > 1.0:
            fee *= (multiplier * 0.9) #multiplier fee with tolerance
        else:
            fee *= 1.0
    else:
        multiplier = 1.0

    #Check if fee is right
    user_fee = user_block.balance - worker_block.balance
    if user_fee < fee:
        print ( "Fee " + str(user_fee) + " is less than minimum " + str(fee))
        return {"Error": "Fee is less than minimum"}

    #Check previous block
    if frontier(user_block.account) == user_block.previous:
        print ("Block is valid: " + user_block.block_hash)
    else:
        print ("Gap previous block")
        return {"Error": "Gap previous block"}

    #Check if account source has sufficient funds for both transactions
    if balance(user_block.account) < int(worker_block.balance):
        print ("Insufficient funds")
        return {"Error": "Insuficient funds"}
    else:
        print ("Account has sufficient funds")

    #If all is right, check active_difficulty and PoW both transactions
    print ("Solving Works...")
    user_block.work = solve_work(user_block.previous, multiplier)
    print ("User transaction: work done")
    worker_block.work = solve_work(worker_block.previous, multiplier)
    print ("Worker transaction: work done")

    #Broadcast
    r_user = broadcast(user_block.json())
    r_worker = broadcast(worker_block.json())

    #response
    if 'hash' in r_user:
        print ("User transaction successful! Block:" + r_user.get("hash"))
        response = {"Successful": r_user["hash"]}

        if 'hash' in r_worker:
            print ("Worker transaction successful! Block:" + r_worker["hash"])
            print ("Your reward has arrived!")
        else:
            print ("Worker transaction fail. Details: " + json.dumps(r_worker))
    else:
        print ("User transaction fail. Details: " + json.dumps(r_user) + "\n")
        response = {"Error": "User transaction fail. Details: " + json.dumps(r_user)}

    print ("\n")
    return response

waitress.serve(app, host='0.0.0.0', port=service_port)

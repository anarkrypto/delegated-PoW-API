from flask import Flask, jsonify, request
from functions import block_create, check_balance, check_block, broadcast, worker_account, minimum_fee
from nanolib import Block

import requests
import json

app = Flask(__name__)


@app.route('/opening_request', methods=['GET', 'POST'])
def opening_request():
    return worker_account


@app.route('/request_pow', methods=['GET', 'POST'])
def request_pow():

    #request transactions
    data = request.get_json()

    #check if user and worker transaction is present
    if "user_transaction" in data:
        user = data.get("user_transaction")
    else:
        print ("User transaction missing")
        return {"Error": "User transaction is missing"}

    if "user_transaction" in data:
        worker = data.get("worker_transaction")
    else:
        print ("Worker transaction missing")
        return {"Error": "Worker transaction is missing"}


    #Read transaction and check if is valid
    user_block = block_create(user.get('block_type'), user.get('account'), user.get('representative'), user.get('previous'), user.get("link_as_account"), user.get("signature"), int(user.get('balance')))
    if user_block == "invalid":
        print ("Invalid user transaction")
        return '{"Error": "Invalid user transaction"}'
    worker_block = block_create(worker.get('block_type'), worker.get('account'), worker.get('representative'), worker.get('previous'), worker.get("link_as_account"), worker.get("signature"), int(worker.get('balance')))
    if worker_block == "invalid":
        print ("Invalid worker transaction")
        return {"Error": "Invalid worker transaction"}

    #If account source in both transactions is different
    if user_block.account != worker_block.account :
        print ("Different Accounts source")
        return '{"Error": "Different Accounts source"}'

    #If worker account is wrong
    if worker_block.link_as_account != worker_account:
        print("Worker account is wrong")
        return {"Error": "Worker account is wrong"}


    #Check if previous block in worker hash is correct
    if worker_block.previous != user_block.block_hash:
        print ("Incorrect Previous Block on Worker Block")
        return {"Error": "Incorrect Previous Block on Worker Block" }

    #Check if fee is right
    fee = user_block.balance - worker_block.balance
    if fee  < minimum_fee:
        print ("Fee is less than minimum")
        return {"Error": "Fee " + str(fee) + " is less than minimum " + str(minimum_fee)}

    #Check if user block already exists
    if check_block(user_block.block_hash) == "exists":
        print ("User Block already exists")
        return {"Error": "User block already exists"}

    #Check if account source have suficiente funds for both transactions
    if check_balance(user_block.account, int(worker_block.balance)) is False:
        print ("Insufficient funds")
        return {"Error": "Insuficient funds!"}
    else:
        print ("Account have sufficient funds")


    #If all is right, make the PoW of both transactions
    user_block.solve_work()
    print ("User Transaction Work Done")
    worker_block.solve_work()
    print ("Worker Transaction Work Done")


    #Broadcast
    r_user = broadcast(user_block.json())
    r_worker = broadcast(worker_block.json())


    #response
    if 'hash' in r_user:
        print ("User Transaction Successful! Block:" + r_user.get("hash") + "\n")
        response = {"Successful": r_user["hash"]}

        if 'hash' in r_worker:
            print ("Worker Transaction Successful! Block:" + r_user["hash"] + "\n")
        else:
            print ("Worker Transaction Fail. Details: " + json.dumps(r_worker) + "\n")

    else:
        print ("User Transaction Fail. Details: " + json.dumps(r_user) + "\n")
        response = {"Error": "User Transaction Fail. Details: " + json.dumps(r_user)}

    return response

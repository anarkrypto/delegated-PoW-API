from nanolib import Block
import json
import requests

#Import config
with open('config.json') as config_file:
    data = json.load(config_file)

worker_account = data['reward_address']
minimum_fee = data['minimum_fee']
node = data['node_url']

#Read transaction Block
def block_create(block_type, account, representative, previous, link_as_account, signature, balance):
    try:
        block = Block(
            block_type=block_type,
            account=account,
            representative=representative,
            previous=previous,
            link_as_account=link_as_account,
            signature=signature,
            balance=balance
        )
    except:
        return "invalid"
    else:
        return block


#check if the account has the balance
def check_balance(address, balance):
    data = {
        "action": "account_balance",
        "account": address
    }
    resp = json.loads(requests.post(node, json=data).text)
    if int(resp['balance']) >= int(balance):
        return True
    return False


#check if block already exists
def check_block(hash):
    data = {
        "action": "block_info",
        "json_block": "true",
        "hash": hash
    }
    resp = json.loads(requests.post(node, json=data).text)
    if 'error' in resp:
        return "valid"
    else:
        return "exists"



#broadcast transaction
def broadcast(transaction):
    request = requests.post(node, json={"action": "process", "json_block": "true", "block": json.loads(transaction)})
    return json.loads(request.text)

import configparser
import requests
import asyncio
import websockets
import json
import time
import base64

def PrintLogo():
    print("""
 _     _                                 
| |__ (_) __ _ _ __ ___   ___  _ __ ___  
| '_ \| |/ _` | '_ ` _ \ / _ \| '_ ` _ \ 
| |_) | | (_| | | | | | | (_) | | | | | |
|_.__/|_|\__, |_| |_| |_|\___/|_| |_| |_| v1.0
         |___/                           
    by: Dyrandy
""")
    
def CheckConnection(gql_url, token):
    print("[*] Checking Connection...")
    headers = {
        'Authorization': f'Bearer {token}'
    }
    connectionQuery = '''query Viewer{
  viewer {
    id
    profile{
      identity{
        email
        name
      }
    }
  }
}'''
    try:
        response = requests.post(url=gql_url, headers=headers, json={'query': connectionQuery})
        response.raise_for_status()
        print("[*] Connection Established!")
        print("[*] Welcome, " + response.json()['data']['viewer']['profile']['identity']['name'])
    except requests.exceptions.HTTPError as err:
        print(err)
        print("Connection Failed! (Check your connection or token)")
        exit()
    

def PrintAndSelectMenu():
    print("\n[*] Select an option:")
    print("[1] Get Current Project")
    print("[2] Match and Replace 'If-None-Match' & 'If-Modified-Since' Header")
    print("[3] Analyze History")
    print("[4] Subscription Mode")
    print("[0] Exit")
    print("> ", end="")
    return input()
    

def SubscriptionMode():
    print("[*] Subscription Will Analyze and Add New Requests and Responses For Potential Findings")
    print("[*] Starting Subscription...")

def GetResponseFromRequest(gql_url, token, id):
    query = '''
query{
  request(id:"''' + id + '''"){
    response{
      id
      raw
    }
  }
}
'''
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = None
    # print("[*] Waiting for Response...", end="")
    while response == None:
        response = requests.post(url=gql_url, headers=headers, json={'query': query})
        response.raise_for_status()
        if response.json()['data']['request']['response'] == None:
            # print(".", end="")
            response = None
        else:
            # print()
            # print("[*] Response Received!")
            # print(response.json())
            break
    # print(response.json())
    return response.json()['data']['request']['response']['raw']

def CheckReflection(gql_url, token, data):
    respData = GetResponseFromRequest(gql_url, token, data['id'])
    reqData = data['raw']
    respDataTxt = base64.b64decode(respData)#.decode('utf-8')
    reqDataTxt = base64.b64decode(reqData)#.decode('utf-8')
    # print(respDataTxt)
    # print(reqDataTxt)
    # print("[*] Checking Reflection...")



async def subscribe_to_created_request():
    ws_url = config['info']['WS_URI']
    token = config['info']['CAIDO_AUTHENTICATION']
    headers = {
        'Authorization': f'Bearer {token}'
    }
    subscription_query = {
        "type": "start",
        "id": "1",  # Arbitrary ID for the operation
        "payload": {
            "query": """
            subscription {
              createdRequest {
                requestEdge {
                  node {
                    id
                    host
                    path
                    method
                    query
                    raw
                  }
                }
              }
            }
            """
        }
    }

    async with websockets.connect(ws_url, extra_headers=headers, subprotocols=['graphql-transport-ws']) as websocket:
        # Send a connection initialization message
        await websocket.send(json.dumps({
            "type": "connection_init",
            "payload": {
                "Authorization": f"Bearer {token}"
            }
        }))

        # Wait for connection acknowledgment
        response = await websocket.recv()
        print("[+] Connection initialized:", response)

        # Send the subscription query
        await websocket.send(json.dumps(subscription_query))

        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                # print(data)
                if data['type'] == 'next':
                    # print("[*] Received data:", data['payload']['data'])
                    # print("[*] Received data:", data['payload']['data']['createdRequest']['requestEdge']['node'])
                    node = data['payload']['data']['createdRequest']['requestEdge']['node']
                    CheckReflection(config['info']['GRAPHQL_URI'], token, node)
                elif data['type'] == 'error':
                    print("[*] Received error:", data['payload']['errors'])
                elif data['type'] == 'complete':
                    print("[*] Subscription completed")
                    break
        except websockets.ConnectionClosed:
            print("[-] Connection closed")

async def monitor_keyboard(websocket):
    while True:
        user_input = await asyncio.to_thread(input, "[*] Press 'q' to quit: ")
        if user_input.lower() == 'q':
            print("[*] Quitting and closing connection...")
            await websocket.close()
            break

async def doSubscription(ws_url, token):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    async with websockets.connect(ws_url, extra_headers=headers, subprotocols=['graphql-transport-ws']) as websocket:
        # Start the subscription in a background task
        subscription_task = asyncio.create_task(subscribe_to_created_request())

        # Monitor keyboard input in another task
        keyboard_task = asyncio.create_task(monitor_keyboard(websocket))

        # Wait for either task to complete
        await asyncio.wait([subscription_task, keyboard_task], return_when=asyncio.FIRST_COMPLETED)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    PrintLogo()
    CheckConnection(config['info']['GRAPHQL_URI'], config['info']['CAIDO_AUTHENTICATION'])
    option = PrintAndSelectMenu()
    while option != '0':
        if option == '1':
            print("[*] Getting Current Project...")
            exit()
        elif option == '2':
            print("[*] Match and Replace 'If-None-Match' & 'If-Modified-Since' Header...")
            exit()
        elif option == '3':
            print("[*] Analyzing History...")
            exit()
        elif option == '4':
            print("[*] Subscription Mode...")
            asyncio.run(doSubscription(config['info']['WS_URI'],config['info']['CAIDO_AUTHENTICATION']))
        option = PrintAndSelectMenu()
    
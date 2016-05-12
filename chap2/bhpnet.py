import sys
import socket
import getopt
import threading
import subprocess

listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0


def usage():
    msg = "BHP Net Tool\n" \
        + "\n" \
        + "Usage: bhpnet.py -t target_host -p port" \
        + " And So On!"
    print(msg)


def main():
    global listen
    global port
    global command
    global upload
    global execute
    global target
    global upload_destination

    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hle:t:p:cu:",
                                   ["help", "listen", "execute=", "target=",
                                    "port=", "command", "upload="])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--commandshell"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

    if not listen and len(target) and port > 0:
        buffer = sys.stdin.read()

        client_sender(buffer)

    if listen:
        server_loop()


def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((target, port))

        if len(buffer):
            client.send(buffer.encode('utf-8'))

        while True:
            recv_len = 1
            response = b""

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data
                if recv_len < 4096:
                    break

            print(response.decode('utf-8'), end='')

            buffer = input("")
            buffer += '\n'

            client.send(buffer.encode('utf-8'))

    except Exception as e:
        print(e)
        print("[*] Exception! Exiting...")
        client.close()


def server_loop():
    global target

    if not len(target):
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind((target, port))

    server.listen(5)

    while True:
        print("waiting accept")
        client_socket, addr = server.accept()
        print("accepted")

        client_thread = threading.Thread(target=client_handler,
                                         args=(client_socket,))
        client_thread.start()


def run_command(command):
    command = command.rstrip()

    try:
        output = subprocess.check_output(command,
                                         stderr=subprocess.STDOUT, shell=True)
    except:
        output = b"Failed to execute command.\r\n"

    return output


def recv_file_data(client_socket):
    file_buffer = ""

    while True:
        data = client_socket.recv(1024)

        if len(data) == 0:
            break
        else:
            file_buffer += data

    return file_buffer


def client_handler(client_socket):
    global upload
    global execute
    global command

    if len(upload_destination):
        data = recv_file_data(client_socket)

        try:
            fd = open(upload_destination, "wb")
            fd.write(data)
            fd.close()

            client_socket.send(b"Successfully saved file to %s\r\n"
                               % upload_destination)
        except:
            client_socket.send(b"Failed to save file to %s\r\n"
                               % upload_destination)

    if len(execute):
        output = run_command(execute)

        client_socket.send(output.encode('utf-8'))

    if command:
        prompt = b"<BHP:#>"
        client_socket.send(prompt)

        while True:
            cmd_buffer = b""
            while b'\n' not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)
                if not len(cmd_buffer):
                    break

            response = run_command(cmd_buffer)
            response += prompt
            try:
                client_socket.send(response)
            except:
                print("connection closed")
                client_socket.close()
                return


if __name__ == '__main__':
    main()

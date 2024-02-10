from socket import socket, AF_INET, SOCK_STREAM

from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import (
    QApplication, 
    QWidget, 
    QPushButton, 
    QLabel, 
    QHBoxLayout,
    QLineEdit, 
    QVBoxLayout, 
    QSizePolicy, 
    QSpacerItem,
    QListWidget,
    QTextEdit,
    QListWidgetItem,
    QTextEdit,
    QMessageBox,
    QPlainTextEdit
)
from PyQt6.QtCore import (
    Qt,
    QSize,
    QTimer,
    QThread, 
    QObject, 
    pyqtSignal,
    QRegularExpression

)
import sys
import json
import platform
import uuid
# CONSTANTS
REFRESH_TIME = 15000
## Network configuration
# ADDRESS = "localhost"
PORT = 50000
BUF_SIZE = 1024 * 1024


# hostname = platform.node()

# Working
def serverFetchRequest(username, hostname):
    server = (hostname, PORT)
    serverResponse = None

    try:
        with socket(AF_INET, SOCK_STREAM) as client:
            client.connect(server)
            payload = f'''Request-Type: Fetch


User: {username}@{hostname}


REQUEST END


'''
            client.sendall(payload.encode("utf-8"))
            serverResponse = client.recv(BUF_SIZE).decode("utf-8")
            
            if serverResponse[-2] == ',':
                serverResponse = removeTrailingComma(serverResponse)            

    except OSError as e:
        print(f"Error connecting to server: {e}")
        return []
    
    try:
        receivedEmails = json.loads(serverResponse)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        receivedEmails=[]

    return receivedEmails


# Working
def serverSendRequest(message, username, receiver, subject, hostname):
    server = (hostname, PORT)
    serverResponse = None
    if not subject:
        subject = "(Brak tytułu)"
    # if not message:
    #     message = "BRAK"
    try:
        with socket(AF_INET, SOCK_STREAM) as client:
            client.connect(server)
            payload = f'''Request-Type: Send


Content-Length: {len(message.strip())}
Sender: {username}@{hostname}
Receiver: {receiver.strip()}
Subject: {subject.strip()}


{message.strip()}


REQUEST END


'''
            client.sendall(payload.encode("utf-8"))
            serverResponse = client.recv(BUF_SIZE).decode("utf-8")
            if serverResponse == "Success" or serverResponse == "Forwarded":
                return "OK"
            else:
                return "Err"

    except ConnectionResetError as e:
        print(f"Connection reset by the server: {e}")
        return "Could not deliver your email"
    except socket.error as e:
        print(f"Error sending request to server: {e}")
        return "Could not deliver your email"



def removeTrailingComma(serverResponse):
    #Split string into 2 pieces, remove ',' and join it back
    serverResponsePartOne = serverResponse[:-2]
    serverResponsePartTwo = serverResponse[-2:]
    serverResponsePartTwoList = list(serverResponsePartTwo)
    serverResponsePartTwoList.pop(0)
    serverResponsePartTwo = ''.join(serverResponsePartTwoList)
    serverResponse = serverResponsePartOne + serverResponsePartTwo
    return serverResponse




class Worker(QObject):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onTimeout)
        self.timer.start(REFRESH_TIME)

    def onTimeout(self):
        self.signal.emit()



class AuthWindow(QWidget):
    def __init__(self, mainWindow):
        super().__init__()
        self.mainWindow = mainWindow
        self.initUI()

    def initUI(self):
        hbox = QHBoxLayout()
        vbox = QVBoxLayout()
        self.setWindowTitle("Login")

        topSpacer = QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        vbox.addItem(topSpacer)
        
        emailLabel = QLabel("Username: ")
        emailLabel.setFixedSize(150, 25)
        vbox.addWidget(emailLabel)

        self.username = QLineEdit()
        self.username.setFixedSize(150, 25)
        vbox.addWidget(self.username)
        self.mainWindow.setUsername(self.username)
        
        loginButton = QPushButton("Login")
        loginButton.clicked.connect(self.validateAndGoToMainWindow)
        loginButton.setFixedSize(150, 25)
        
        vbox.addWidget(loginButton)
        
        bottom_spacer = QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        vbox.addItem(bottom_spacer)

        hbox.addLayout(vbox)
        self.setLayout(hbox)


    def validateAndGoToMainWindow(self):
        re=QRegularExpression("([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+")
        match = re.match(self.username.text())
        errorBox = QMessageBox(self)
        errorBox.setIcon(QMessageBox.Icon.Critical)
        errorBox.setWindowTitle("Error")
        if match.hasMatch():
            self.mainWindow.setWindowTitle(f"User logged in : {self.username.text()}")
            self.mainWindow.show()
            self.hide()
        elif not self.username.text():
            errorBox.setText("Email address can't be empty")
            errorBox.exec()
        else:
            errorBox.setText("Email address has incorrect format")
            errorBox.exec()
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.username = 'nousername'
        self.initUI()
        self.defaultUI = True

    def showEvent(self, a0: QShowEvent | None) -> None:
        self.refreshEmailList()
        return super().showEvent(a0)

    def setUsername(self, username):
        self.username = username      

    def initUI(self):
        self.refreshEmailList
        self.resize(800,600)
        layout = QHBoxLayout(self)

        # Worker class instance
        self.worker = Worker()
        # Create thread that will execute onRefreshSignal function every REFRESH_TIME/1000 seconds
        self.workerThread = QThread()
        self.worker.signal.connect(self.onRefreshSignal)
        self.worker.moveToThread(self.workerThread)
        self.workerThread.started.connect(self.worker.timer.start)
        self.workerThread.start()

        # First Column
        firstColumn = QVBoxLayout()
        sendEmailButton = QPushButton("New email", self)
        sendEmailButton.clicked.connect(self.changeToEditableLayout)
        firstColumn.addWidget(sendEmailButton)

        firstColumnWidget = QWidget()
        firstColumnWidget.setLayout(firstColumn)
        firstColumnWidget.setFixedSize(100, 600)


        # Second column
        secondColumn = QVBoxLayout()
        # Email list inside Second Column
        self.emailList = QListWidget(self)
        
        self.emailList.itemClicked.connect(self.showEmailContet)

        secondColumnWidget = QWidget()
        
        secondColumnWidget.setLayout(secondColumn)
        secondColumnWidget.setFixedSize(200, 600)

        secondColumn.addWidget(self.emailList)
        

        # Refresh email list button
        refreshEmailButton = QPushButton("Refresh", self)
        refreshEmailButton.clicked.connect(self.refreshEmailList)
        secondColumn.addWidget(refreshEmailButton)

        # Third column
        thirdColumn = QVBoxLayout()
        # FROM, TOPIC placeholders
        self.senderLabel = QLabel("From: ")
        self.topicLabel = QLabel("Topic: ")
        # Mail content box
        self.emailContent = QTextEdit(self)
        self.emailContent.setReadOnly(True)

        thirdColumn.addWidget(self.senderLabel)
        thirdColumn.addWidget(self.topicLabel)
        thirdColumn.addWidget(self.emailContent)

        self.thirdColumnWidget = QWidget()
        self.thirdColumnWidget.setLayout(thirdColumn)
        self.thirdColumnWidget.setFixedSize(500, 600)

        # Spacer item to expand on right and left
        horizontalSpacer = QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # All columns to main layout
        layout.addSpacerItem(horizontalSpacer)
        layout.addWidget(firstColumnWidget)
        layout.addWidget(secondColumnWidget)
        layout.addWidget(self.thirdColumnWidget)
        layout.addSpacerItem(horizontalSpacer)


    def changeToEditableLayout(self):
        # Remove current third column widgets
        self.defaultUI = False
        self.senderLabel.setParent(None)
        self.topicLabel.setParent(None)
        self.emailContent.setParent(None)

        # Input fields for email and subject
        self.receiverTextEdit = QLineEdit()
        self.subjectTextEdit = QLineEdit()
        self.emailLabel = QLabel("To: ")
        self.subjectLabel = QLabel("Subject: ")

        # Email and subject rows layout
        emailInputLayout = QHBoxLayout()
        emailInputLayout.addWidget(self.emailLabel)
        emailInputLayout.addWidget(self.receiverTextEdit)

        subjectInputLayout = QHBoxLayout()
        subjectInputLayout.addWidget(self.subjectLabel)
        subjectInputLayout.addWidget(self.subjectTextEdit)

        # Editable email content
        self.emailContentTextEdit = QPlainTextEdit()

        # Email sending layout
        thirdColumn = QVBoxLayout()
        thirdColumn.addLayout(emailInputLayout)
        thirdColumn.addLayout(subjectInputLayout)
        thirdColumn.addWidget(self.emailContentTextEdit)

        # Send button
        sendButton = QPushButton("Send")
        sendButton.clicked.connect(self.sendEmail)
        

        thirdColumn.addWidget(sendButton)

        thirdColumnWidget = QWidget()
        thirdColumnWidget.setLayout(thirdColumn)
        thirdColumnWidget.setFixedSize(500, 600)

        # Replacing layout
        self.layout().replaceWidget(self.thirdColumnWidget, thirdColumnWidget)

        # Newly created column reference
        self.thirdColumnWidget = thirdColumnWidget
    def sendEmail(self):
            message = self.emailContentTextEdit.toPlainText()
            userInfo = self.username.text().split('@')

            re=QRegularExpression("([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+")
            match = re.match(self.receiverTextEdit.text())
            errorBox = QMessageBox(self)
            errorBox.setIcon(QMessageBox.Icon.Critical)
            errorBox.setWindowTitle("Error")
            if match.hasMatch():
                receiver = self.receiverTextEdit.text()
            elif not self.receiverTextEdit.text():
                errorBox.setText("Email address can't be empty")
                errorBox.exec()
            else:
                errorBox.setText("Email address has incorrect format")
                errorBox.exec()        

            subject = self.subjectTextEdit.text()
            if message == '':
                errorBox = QMessageBox(self)
                errorBox.setIcon(QMessageBox.Icon.Critical)
                errorBox.setWindowTitle("Error")
                errorBox.setText("Treść maila nie może być pusta")
                errorBox.exec()
            else:
                serverResponse = serverSendRequest(message, userInfo[0], receiver, subject, userInfo[1])
                if serverResponse == 'OK':
                    self.restartUI()
                    errorBox = QMessageBox(self)
                    errorBox.setWindowTitle("Sent")
                    errorBox.setText("Email sent")
                    errorBox.exec()
                else:
                    errorBox = QMessageBox(self)
                    errorBox.setWindowTitle("Error")
                    errorBox.setText("Unable to send your email")
                    errorBox.exec()
            
    #Restores UI third Column to initial state if state has been modified
    def restartUI(self):
        if not self.defaultUI:
            self.receiverTextEdit.setParent(None)
            self.subjectTextEdit.setParent(None)
            self.emailContentTextEdit.setParent(None)
            self.emailLabel.setParent(None)
            self.subjectLabel.setParent(None)
            # Third column
            thirdColumn = QVBoxLayout()
            # FROM, TOPIC placeholders
            self.senderLabel = QLabel("From: ")
            self.topicLabel = QLabel("Topic: ")
            # Mail content box
            self.emailContent = QTextEdit(self)
            self.emailContent.setReadOnly(True)

            thirdColumn.addWidget(self.senderLabel)
            thirdColumn.addWidget(self.topicLabel)
            thirdColumn.addWidget(self.emailContent)

            thirdColumnWidget = QWidget()
            thirdColumnWidget.setLayout(thirdColumn)
            thirdColumnWidget.setFixedSize(500, 600)
            self.layout().replaceWidget(self.thirdColumnWidget, thirdColumnWidget)
            self.thirdColumnWidget = thirdColumnWidget
            self.defaultUI = True

    #Display email content of clicked email item from email list        
    def showEmailContet(self, item):
        self.restartUI()
        # Selecting widget that was clicked
        clickedWidget = self.emailList.itemWidget(item)
        # get sender, subject
        richText = clickedWidget.text()
        senderIndex = richText.find("<b>")
        sender = richText[senderIndex + 3 : richText.find("</b>", senderIndex)]
        subjectIndex = richText.find("<br/>") + 5
        subject = richText[subjectIndex:]
        # hash of selected item
        clickedEmailId = clickedWidget.objectName()

        # Looks for email with ceratin sender and subject, if not found return None
        selectedEmail = next(
            (email for email in self.receivedEmails if email["emailId"] == clickedEmailId and email["sender"] == sender and email["subject"] == subject), None
        )

        # Shows selectedEmail in mail content box
        
        if selectedEmail:
            self.emailContent.setPlainText(selectedEmail["message"])
            self.senderLabel.setText(f"From: {selectedEmail['sender']}")
            self.topicLabel.setText(f"Topic: {selectedEmail['subject']}")

    #   Updates the email list on start and after "Refresh" button is clicked
    def updateEmailList(self, receivedEmails):
        self.emailList.clear()
        self.receivedEmails = []    
        for email in receivedEmails:
            #Randomly generated hash to make every mail unique, usefull for searching
            emailId = uuid.uuid4().hex
            sender = email['sender']
            subject = email['subject']
            emailItemOnList = f"<b>{sender}</b><br/>{subject}"
            singleEmail = QLabel(emailItemOnList, objectName = emailId)
            singleEmail.setTextFormat(Qt.TextFormat.RichText)

            item = QListWidgetItem()
            item.setSizeHint(singleEmail.sizeHint() + QSize(0, 10))
            singleEmail.setStyleSheet("border: 1px solid black; opacity: 0.2;")
            self.emailList.addItem(item)
            self.emailList.setItemWidget(item, singleEmail)

            # Add the valid email to the receivedEmails list
            email["emailId"] = emailId
            self.receivedEmails.append(email)
            # print(emailId)

    # function that send fetch request to server and executes updateEmailList with fetched list of emails from server
    def refreshEmailList(self):
        re=QRegularExpression("([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+")
        match = re.match(self.username.text())
        if match.hasMatch():
            userInfo = self.username.text().split('@')
            self.updateEmailList(serverFetchRequest(userInfo[0], userInfo[1]))
        else:
            return


    # Function called every 15 seconds by Refresh instance
    def onRefreshSignal(self):
        self.refreshEmailList()


def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    loginWindow = AuthWindow(mainWindow)
    loginWindow.show()
    
 

    sys.exit(app.exec())
    
if __name__ == '__main__':
    main()
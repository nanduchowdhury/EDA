

1. Install Windows Subsystem for Linux in laptop.

    a. The following command should ideally install WSL in laptop pshell - but somehow it doesn't.
    
        wsl --Install
    
    b. Run following commands from power-shell:

        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

    c. Run following to set default version:

        wsl --set-default-version 2

2. Now open the Ubuntu Linux shell - and start kafka server:

        sudo apt update
        sudo apt upgrade -y
        sudo apt install default-jdk wget -y

        Download kafka

        mkdir kafka
        cd kafka
        wget https://downloads.apache.org/kafka/4.1.0/kafka_2.13-4.1.0.tgz
        tar -xvzf kafka_2.13-4.1.0.tgz
        cd kafka_2.13-4.1.0/

        Check Java version

        java -version
        sudo apt update
        sudo apt install openjdk-17-jdk -y
        java -version
        
        Set storage for kafka

        uuidgen
        mkdir /tmp/kraft-logs
        bin/kafka-storage.sh format -t c616e58a-5c49-40de-9d8c-d9078eb81a87 -c config/server.properties
        sudo update-alternatives --config java

        Start kafka server

        KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
        bin/kafka-storage.sh format --standalone -t $KAFKA_CLUSTER_ID -c config/server.properties
        bin/kafka-server-start.sh config/server.properties


3.  Test kafka server

        cd kafka_2.13-4.1.0/
        bin/kafka-topics.sh --create --topic quickstart-events --bootstrap-server localhost:9092
        
        bin/kafka-console-producer.sh --topic quickstart-events --bootstrap-server localhost:9092
        [ write some messages ]

        bin/kafka-console-consumer.sh --topic quickstart-events --from-beginning --bootstrap-server localhost:9092
        [ you will see the same messages being read ]


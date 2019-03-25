FROM ubuntu:18.04

ENV TZ=Europe/Warsaw
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone 

RUN apt update && apt install -y \
  jupyter-core \
  jupyter-notebook \
  openjdk-8-jdk \
  python3-pip \
  wget \
  unzip \
  vim \
  git


RUN pip3 install \
  seaborn \
  scipy \
  numpy \
  requests \
  rasa_nlu \
  sklearn_crfsuite \
  slackclient \
  spacy\
  gtts\
  matplotlib \
  jellyfish \
  pandas \
  sklearn \
  cherrypy\
  pydub\
  six \
  nltk \
  rasa_core \
  gensim \
  tensorflow \
  tensorlayer \
  keras \
  textblob \
  stanfordcorenlp \
  flask \
  tensorboard \
  jupyter-tensorboard

EXPOSE 8888
EXPOSE 9000
EXPOSE 5000
EXPOSE 5050
EXPOSE 6006

RUN jupyter-tensorboard enable --system
RUN python3 -m spacy download en
RUN useradd -ms /bin/bash codete
RUN adduser codete sudo

USER codete
WORKDIR /home/codete/
RUN mkdir /home/codete/workshop/
RUN mkdir /home/codete/workshop/tensorboard/
RUN mkdir /home/codete/workshop/tensorboard/logs/
RUN python3 -m nltk.downloader all
RUN wget http://nlp.stanford.edu/software/stanford-corenlp-full-2018-10-05.zip
RUN unzip stanford-corenlp-full-2018-10-05.zip
RUN tensorboard --logdir /home/codete/workshop/tensorboard/logs/ &
CMD jupyter-notebook --ip=0.0.0.0 --NotebookApp.token='' --NotebookApp.password='' --no-browser --notebook-dir=/home/codete/workshop/

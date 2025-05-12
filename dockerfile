FROM python


# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gcc \
      unixodbc \
      unixodbc-dev \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSL -O https://packages.microsoft.com/config/ubuntu/$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2)/packages-microsoft-prod.deb && sudo dpkg -i packages-microsoft-prod.deb && rm packages-microsoft-prod.deb && sudo apt-get update && sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 && sudo ACCEPT_EULA=Y apt-get install -y mssql-tools18 && echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc

# 2) Now pyodbc can find libodbc.so.2
RUN pip install --no-cache-dir pyodbc

# Install any needed packages specified in requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt

# Install db stuff

# Make port 80 available to the world outside this container (Optional, only for web apps)
EXPOSE 28752

# Run app.py when the container launches
CMD ["python", "./server.py"]

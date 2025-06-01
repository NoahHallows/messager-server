FROM python:3.14.0b1-bookworm


# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

RUN apt-get update

# Install any needed packages specified in requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container (Optional, only for web apps)
EXPOSE 28752

# Run app.py when the container launches
CMD ["python", "./server.py"]

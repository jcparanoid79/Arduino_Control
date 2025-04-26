from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

try:
    with open("./requirements.txt", "r") as fh:
        requirements = fh.read().splitlines()
except FileNotFoundError:
    requirements = []

setup(
    name='arduino_control',
    version='0.1.0',
    author="Your Name",
    author_email="your.email@example.com",
    description='A package to control Arduino boards',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your_username/arduino_control",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=requirements,
)

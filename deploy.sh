#!/bin/bash

# Business Analyzer - Docker Deployment Script
# This script helps you quickly build and deploy the application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="business-analyzer"
CONTAINER_NAME="business-analyzer-app"
PORT=8501

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Business Analyzer - Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is installed${NC}"
}

# Function to check if Docker is running
check_docker_running() {
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker is not running${NC}"
        echo "Please start Docker and try again"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Function to build Docker image
build_image() {
    echo ""
    echo -e "${YELLOW}Building Docker image...${NC}"
    docker build -t ${IMAGE_NAME}:latest .
    echo -e "${GREEN}✓ Image built successfully${NC}"
}

# Function to stop and remove existing container
cleanup_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo ""
        echo -e "${YELLOW}Stopping and removing existing container...${NC}"
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    fi
}

# Function to create data directory
create_data_dir() {
    if [ ! -d "./data" ]; then
        echo ""
        echo -e "${YELLOW}Creating data directory...${NC}"
        mkdir -p ./data
        echo -e "${GREEN}✓ Data directory created${NC}"
    fi
}

# Function to run container
run_container() {
    echo ""
    echo -e "${YELLOW}Starting container...${NC}"
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p ${PORT}:${PORT} \
            -v $(pwd)/data:/app/data \
            --env-file .env \
            --restart unless-stopped \
            ${IMAGE_NAME}:latest
    else
        echo -e "${YELLOW}Warning: .env file not found. Using default configuration.${NC}"
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p ${PORT}:${PORT} \
            -v $(pwd)/data:/app/data \
            --restart unless-stopped \
            ${IMAGE_NAME}:latest
    fi
    
    echo -e "${GREEN}✓ Container started successfully${NC}"
}

# Function to show container status
show_status() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Container Name: ${CONTAINER_NAME}"
    echo "Image: ${IMAGE_NAME}:latest"
    echo "Port: ${PORT}"
    echo ""
    echo -e "${GREEN}Access your application at:${NC}"
    echo "  http://localhost:${PORT}"
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo "  View logs:    docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:         docker stop ${CONTAINER_NAME}"
    echo "  Start:        docker start ${CONTAINER_NAME}"
    echo "  Restart:      docker restart ${CONTAINER_NAME}"
    echo "  Remove:       docker rm -f ${CONTAINER_NAME}"
    echo ""
}

# Function to show logs
show_logs() {
    echo ""
    echo -e "${YELLOW}Showing container logs (Ctrl+C to exit)...${NC}"
    sleep 2
    docker logs -f ${CONTAINER_NAME}
}

# Main deployment flow
main() {
    # Parse command line arguments
    case "${1:-}" in
        "build")
            check_docker
            check_docker_running
            build_image
            ;;
        "run")
            check_docker
            check_docker_running
            cleanup_container
            create_data_dir
            run_container
            show_status
            ;;
        "deploy")
            check_docker
            check_docker_running
            build_image
            cleanup_container
            create_data_dir
            run_container
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "stop")
            echo -e "${YELLOW}Stopping container...${NC}"
            docker stop ${CONTAINER_NAME}
            echo -e "${GREEN}✓ Container stopped${NC}"
            ;;
        "start")
            echo -e "${YELLOW}Starting container...${NC}"
            docker start ${CONTAINER_NAME}
            echo -e "${GREEN}✓ Container started${NC}"
            echo "Access at: http://localhost:${PORT}"
            ;;
        "restart")
            echo -e "${YELLOW}Restarting container...${NC}"
            docker restart ${CONTAINER_NAME}
            echo -e "${GREEN}✓ Container restarted${NC}"
            ;;
        "clean")
            echo -e "${YELLOW}Cleaning up...${NC}"
            docker stop ${CONTAINER_NAME} 2>/dev/null || true
            docker rm ${CONTAINER_NAME} 2>/dev/null || true
            docker rmi ${IMAGE_NAME}:latest 2>/dev/null || true
            echo -e "${GREEN}✓ Cleanup complete${NC}"
            ;;
        "status")
            echo ""
            echo -e "${GREEN}Container Status:${NC}"
            docker ps -a --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo ""
            ;;
        *)
            echo "Usage: $0 {build|run|deploy|logs|stop|start|restart|clean|status}"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker image only"
            echo "  run     - Run container (assumes image exists)"
            echo "  deploy  - Build image and run container (full deployment)"
            echo "  logs    - Show container logs"
            echo "  stop    - Stop running container"
            echo "  start   - Start stopped container"
            echo "  restart - Restart container"
            echo "  clean   - Remove container and image"
            echo "  status  - Show container status"
            echo ""
            echo "Examples:"
            echo "  $0 deploy    # Full deployment"
            echo "  $0 logs      # View logs"
            echo "  $0 restart   # Restart app"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

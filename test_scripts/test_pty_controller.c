/*
 * Test PTY Controller for Network Manager Testing
 * 
 * This program creates a PTY (pseudo-terminal) interface to communicate
 * with the embedded application for automated testing.
 */

#define _XOPEN_SOURCE 600
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <termios.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <pty.h>
#include <pthread.h>
#include <stdbool.h>

#define BUFFER_SIZE 4096
#define MAX_RESPONSE_TIME 5 /* seconds */

/* Global variables */
static int master_fd = -1;
static int slave_fd = -1;
static pid_t child_pid = -1;
static bool running = true;
static FILE *log_file = NULL;
static pthread_mutex_t output_mutex = PTHREAD_MUTEX_INITIALIZER;

/* Test result tracking */
typedef struct {
    int total_tests;
    int passed_tests;
    int failed_tests;
    int timeout_tests;
} test_results_t;

static test_results_t results = {0, 0, 0, 0};

/**
 * @brief Signal handler for cleanup
 */
void signal_handler(int sig)
{
    printf("\nReceived signal %d, cleaning up...\n", sig);
    running = false;
    
    if (child_pid > 0) {
        kill(child_pid, SIGTERM);
    }
}

/**
 * @brief Thread function to read output from PTY
 */
void *pty_reader_thread(void *arg)
{
    char buffer[BUFFER_SIZE];
    ssize_t n;
    
    while (running) {
        n = read(master_fd, buffer, sizeof(buffer) - 1);
        if (n > 0) {
            buffer[n] = '\0';
            
            pthread_mutex_lock(&output_mutex);
            printf("%s", buffer);
            fflush(stdout);
            
            if (log_file) {
                fprintf(log_file, "%s", buffer);
                fflush(log_file);
            }
            pthread_mutex_unlock(&output_mutex);
        } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
            perror("read from PTY");
            break;
        }
        
        usleep(10000); /* 10ms delay */
    }
    
    return NULL;
}

/**
 * @brief Send command to PTY
 */
int send_command(const char *cmd)
{
    char cmd_with_newline[256];
    snprintf(cmd_with_newline, sizeof(cmd_with_newline), "%s\r\n", cmd);
    
    ssize_t written = write(master_fd, cmd_with_newline, strlen(cmd_with_newline));
    if (written < 0) {
        perror("write to PTY");
        return -1;
    }
    
    pthread_mutex_lock(&output_mutex);
    printf("[SEND] %s", cmd_with_newline);
    if (log_file) {
        fprintf(log_file, "[SEND] %s", cmd_with_newline);
        fflush(log_file);
    }
    pthread_mutex_unlock(&output_mutex);
    
    return 0;
}

/**
 * @brief Wait for specific response with timeout
 */
bool wait_for_response(const char *expected, int timeout_sec)
{
    char buffer[BUFFER_SIZE];
    time_t start_time = time(NULL);
    
    while ((time(NULL) - start_time) < timeout_sec) {
        ssize_t n = read(master_fd, buffer, sizeof(buffer) - 1);
        if (n > 0) {
            buffer[n] = '\0';
            
            pthread_mutex_lock(&output_mutex);
            printf("%s", buffer);
            if (log_file) {
                fprintf(log_file, "%s", buffer);
                fflush(log_file);
            }
            pthread_mutex_unlock(&output_mutex);
            
            if (strstr(buffer, expected) != NULL) {
                return true;
            }
        }
        
        usleep(100000); /* 100ms delay */
    }
    
    return false;
}

/**
 * @brief Run a test case
 */
void run_test(const char *test_name, const char *command, const char *expected_response)
{
    printf("\n=== Running Test: %s ===\n", test_name);
    results.total_tests++;
    
    if (send_command(command) < 0) {
        printf("FAILED: Could not send command\n");
        results.failed_tests++;
        return;
    }
    
    if (expected_response) {
        if (wait_for_response(expected_response, MAX_RESPONSE_TIME)) {
            printf("PASSED: Got expected response\n");
            results.passed_tests++;
        } else {
            printf("FAILED: Timeout waiting for response '%s'\n", expected_response);
            results.timeout_tests++;
        }
    } else {
        /* No specific response expected, just wait a bit */
        sleep(1);
        printf("PASSED: Command executed\n");
        results.passed_tests++;
    }
}

/**
 * @brief Run network manager test suite
 */
void run_test_suite(void)
{
    printf("\n=== Starting Network Manager Test Suite ===\n");
    
    /* Wait for initialization */
    sleep(3);
    
    /* Test 1: Basic network status */
    run_test("Network Status", "net", "Network:");
    
    /* Test 2: Interface control */
    run_test("Disable ETH0", "net eth0 down", NULL);
    sleep(2);
    run_test("Enable ETH0", "net eth0 up", NULL);
    sleep(5);
    
    /* Test 3: WiFi control */
    run_test("Disable WiFi", "net wlan0 down", NULL);
    sleep(2);
    run_test("Enable WiFi", "net wlan0 up", NULL);
    sleep(5);
    
    /* Test 4: Check interface states */
    run_test("Check Interfaces", "net", "ETH0:");
    
    /* Test 5: Online mode control */
    run_test("Set Offline Mode", "online off", "DISABLED");
    sleep(2);
    run_test("Set Online Mode", "online on", "ENABLED");
    sleep(2);
    
    /* Test 6: Rapid interface switching (hysteresis test) */
    printf("\n=== Hysteresis Test ===\n");
    for (int i = 0; i < 5; i++) {
        send_command("net eth0 down");
        sleep(1);
        send_command("net eth0 up");
        sleep(1);
    }
    run_test("Check Hysteresis", "net", "Status:");
    
    /* Test 7: Configuration display */
    run_test("Show Config", "c", "WiFi Reassociation:");
}

/**
 * @brief Main function
 */
int main(int argc, char *argv[])
{
    char *app_path = NULL;
    char slave_name[256];
    pthread_t reader_thread;
    
    /* Parse arguments */
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <app_path> [log_file]\n", argv[0]);
        return 1;
    }
    
    app_path = argv[1];
    
    /* Open log file if specified */
    if (argc > 2) {
        log_file = fopen(argv[2], "w");
        if (!log_file) {
            perror("fopen log file");
            return 1;
        }
    }
    
    /* Set up signal handlers */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    /* Create PTY */
    if (openpty(&master_fd, &slave_fd, slave_name, NULL, NULL) < 0) {
        perror("openpty");
        return 1;
    }
    
    printf("Created PTY: %s\n", slave_name);
    
    /* Make master non-blocking */
    int flags = fcntl(master_fd, F_GETFL, 0);
    fcntl(master_fd, F_SETFL, flags | O_NONBLOCK);
    
    /* Fork and exec the application */
    child_pid = fork();
    if (child_pid < 0) {
        perror("fork");
        close(master_fd);
        close(slave_fd);
        return 1;
    }
    
    if (child_pid == 0) {
        /* Child process */
        close(master_fd);
        
        /* Redirect stdin, stdout, stderr to slave PTY */
        dup2(slave_fd, STDIN_FILENO);
        dup2(slave_fd, STDOUT_FILENO);
        dup2(slave_fd, STDERR_FILENO);
        
        close(slave_fd);
        
        /* Execute the application */
        execl(app_path, app_path, NULL);
        perror("execl");
        exit(1);
    }
    
    /* Parent process */
    close(slave_fd);
    
    printf("Started application with PID %d\n", child_pid);
    
    /* Start reader thread */
    if (pthread_create(&reader_thread, NULL, pty_reader_thread, NULL) != 0) {
        perror("pthread_create");
        kill(child_pid, SIGTERM);
        close(master_fd);
        return 1;
    }
    
    /* Run test suite */
    run_test_suite();
    
    /* Print results */
    printf("\n=== Test Results ===\n");
    printf("Total tests:   %d\n", results.total_tests);
    printf("Passed:        %d\n", results.passed_tests);
    printf("Failed:        %d\n", results.failed_tests);
    printf("Timeouts:      %d\n", results.timeout_tests);
    printf("Success rate:  %.1f%%\n", 
           results.total_tests > 0 ? 
           (100.0 * results.passed_tests / results.total_tests) : 0.0);
    
    /* Clean up */
    running = false;
    pthread_join(reader_thread, NULL);
    
    if (child_pid > 0) {
        kill(child_pid, SIGTERM);
        waitpid(child_pid, NULL, 0);
    }
    
    close(master_fd);
    
    if (log_file) {
        fclose(log_file);
    }
    
    pthread_mutex_destroy(&output_mutex);
    
    return (results.failed_tests + results.timeout_tests) > 0 ? 1 : 0;
}
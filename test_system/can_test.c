/*
    Copyright (C) 2024 Quake Global Inc. All rights reserved.

    This unpublished source file is the copyrighted intellectual property of
    Quake Global Incorporated, and may not be copied, decompiled, modified,
    or distributed, in whole or in part, without the express written permission
    of the copyright holder. The copyright notice above does not evidence any
    actual or intended publication of such source code.

    Contact information:
    Legal Department
    Quake Global, Inc.
    4711 Viewridge Ave. Suite 150
    San Diego, CA 92123
    858-277-7290

    email: support@quakeglobal.com
*/
/**
    @file CAN_sample.c
    @brief Demonstrates how to utilize the CAN Driver and J1939 module to receive raw and J1939 CAN messages, respectively,
    as well as send CAN messages on the bus. It also demonstrates how to filter the receive buffer to 
    only receive a specified set of CAN IDs.
*/

#include <getopt.h>
#include <stdint.h>
#include <stdio.h>

#include "HostTypes.h"
#include "drivers/CanEvents.h"

bool sendEnabled = FALSE;
bool filtering = FALSE;
CanDrvInterface canIfc = DRV_CAN_IF_NONE ;

/** 
 @brief A buffer of data to be transmitted by sample functions.
 Note CAN frames are limited to 8 bytes of data, so only 0-7 
 are transmitted for raw can.  
 The sample is configured to transmit 8 bytes for j1939 as well,
 but you can modify sendSampleJ1939Message(void) to transmit up 
 to all 32 bytes defined here.
*/
uint8_t dataBuf[] = {
    0,1, 2, 3, 4, 5, 6, 7, 8, 9, 10,11,12,13,14,15,
    16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
};

/**
    @brief This function will transmit a sample pre-defined J1939
    message. For multiframe messages, the buffer length of the data
    (dataBuf) must be specified as greater than the maximum 8 bytes of a
    single frame message. The transmitted multiframe messages will then
    be formatted in accordance with SAE J1939.
    @param pStatus Location for the stack to write status to as the message is processed.
 */
static void sendSampleJ1939Message(uint8_t *pStatus) 
{
    // This function will transmit the first eight bytes of dataBuf
    // (global array defined at the top of this file).  You can change
    // this to a number up to sizeof(dataBuf)==32 to experiment with
    // multiframe transmission.
    const uint16_t bytesToTransmit = 8;

    // Parameter group number
    const unsigned pgn = 0xfebf;

    // Destination field (dst).  255 Is the broadcast destination.
    const uint8_t dst = 255;

    // Source field (src).  Normally, you want to pass J1939_ADDRESS_MINE
    // here, which is a special value that tells the stack to use your 
    // claimed address.  But you can send anything from 0-255 if you want.
    const unsigned src = J1939_ADDRESS_MINE;

    // Priority field.
    const uint8_t pri = 7;

    const char *singleOrMulti ;
    if (bytesToTransmit > 8) {
        singleOrMulti = "multi-" ;
    } else {
        singleOrMulti = "single ";
    }


    fprintf(stdout, "Sending j1939 %sframe message with pgn=%04x\n", singleOrMulti, pgn);

    CANEV_sendJ1939(
        // Location to store status.  The stack will
        // set this to J1939_SEND_INPROCESS, _DONE, and _FAILED to
        // report how things are going. If you are sending multi-frame
        // data, your code is responsible for making sure the buffer you
        // send stays valid until you get a _DONE or _FAILED status.
        pStatus,

        // Which bus you are sending to.  
        canIfc, 

        pgn,

        // pointer to bytes to be transmitted as data, and the number of bytes.
        dataBuf, bytesToTransmit,

        dst, src, pri
    );

    // We don't know immediately whether it succeded; the main loop monitors *pStatus
    // to find out what is happening / has happened.
}

/**
  @brief This function will transmit a sample raw CAN frame.
    
 */
static void sendSampleRawMessage(void) 
{
    // This function will attempt to transmit the first eight bytes of dataBuf.
    // Raw CAN doesn't allow more than eight bytes, but you could
    // set this to a smaller number if you wish.
    const uint16_t bytesToTransmit = 8;

    if (bytesToTransmit > 8) {
        fprintf(stderr, "invalid transmit bytesToTransmit\n") ;
        exit(1);
    }

    // send a CAN message with ID 18FFBC32 and payload 00 01 02 03 04 05 06 07

    const uint32_t CAN_ID = 0x18FFBC32U;

    fprintf(stdout, "Sending raw CAN message with CAN id=%x\n", CAN_ID);

    FaultCode fc = CANEV_sendRawCan(

        // Which CAN bus you are sending to.  Note this bus must have
        // been properly configured with CANEV_init().
        canIfc, 

        // the CAN ID to send out.
        CAN_ID,

        // The data to send, and number of bytes you are sending.
        dataBuf, bytesToTransmit
    );

    if (OK != fc) {
        fprintf(stderr, "sending raw can message failed\n") ;
        exit(1);
    } else {
        fprintf(stdout,"successfully transmitted raw can message.\n");
    }
}


/**
 * @brief Prints usage instructions for the application, as well as examples for different uses.
 */
static void printUsage(void) 
{
    fprintf(stdout, "Low-level CAN Sample App\n");
    fprintf(stdout, "Usage: \n./user_can_lowlevel_sample [OPTION]...\n");
    fprintf(stdout, "Required arguments:\n");
    fprintf(stdout, "-i, --interface INTERFACE \t Selects CAN interface (CAN0/CAN1)\n");
    fprintf(stdout, "-b, --baud BAUDRATE \t Selects baudrate (250kbps/500kbps/1000kbps\n");
    fprintf(stdout, "Optional arguments:\n");
    fprintf(stdout, "-j, --j1939 \t Selects J1939 protocol, disables raw protocol\n");
    fprintf(stdout, "-s, --send \t Sends a raw CAN message if raw protocol is enabled, or sends J1939 message if --j1939 option is selected\n");
    fprintf(stdout, "-f, --filter \t Enables filtering for sample CAN IDs 18FFBC32 & 18FFBC19\n");

    fprintf(stdout,"Examples:\n");
    fprintf(stdout,"./user_can_lowlevel_sample --interface 0 --baud 250 --filter\n");
    fprintf(stdout,"./user_can_lowlevel_sample --interface 1 --baud 500 --j1939 --send\n");
}

static struct option longOptions[] =
{
    {"interface", required_argument, 0, 'i'},
    {"baud", required_argument, 0, 'b'},
    {"j1939", no_argument, 0, 'j'},
    {"send", no_argument, 0, 's'},
    {"filter", no_argument, 0, 'f'},
    {0, 0, 0, 0}
};

/** @brief 
  This is the handler function that we configure for the CAN bus to receive
  raw CAN frames.  It is called whenever a new frame arrives from the bus.
  @param whichBus DRV_CAN_0 or DRV_CAN_1.  Tells which interface received the message.
  @param canId The CAN id from the frame.
  @param buf A pointer to the data from the frame.
  @param bufLen The number of bytes of data sent with the frame in buf.
 */
static void rawFrameHandler(CanDrvInterface whichBus, uint32_t canId, uint8_t *buf, uint8_t bufLen)
{
    // The actual CAN id is 29 bits long.  The upper three bits represent
    // the EFF/RTR/ERR flags.  The below line zeroes those bits, leaving 
    // just the can id itself for printing.
    canId &= CAN_ERR_MASK; 

    fprintf(stdout,"RAW RX: 0x%x -", canId);
    for (int i = 0 ; i < bufLen ; i++) {
        fprintf(stdout," %02x", (unsigned)buf[i]);
    }
    fprintf(stdout,"\n");
}

/** @brief 
  This is the handler function that we configure for the CAN bus to receive
  Incoming j1939 messages.  It is called whenever a message arrives from the 
  bus.
  @param whichBus DRV_CAN_0 or DRV_CAN_1.  Tells which interface received the message.
  @param pgn Parameter Group Number part of the CAN id.
  @param buf A pointer to the data from the frame.
  @param bufLen The number of bytes of data sent with the frame in buf.
  @param dst Destination field
  @param src Source field
  @param pri Priority field.
 */
static void j1939MessageHandler(CanDrvInterface whichBus, uint32_t pgn, uint8_t *buf, uint16_t bufLen, uint8_t dst, uint8_t src, uint8_t pri)
{

    uint32_t recoveredCanId = 
        ((pri & 0x07) << 26) |    // priority bits 26-29.
        ((pgn & 0x1FFFF) << 8) |  // pgn pdu format bits 8-24
        (src & 0xFF);             // source address bits 0-7

    fprintf(stdout,"J1939 RX: %x - PGN=%x dst=%x src=%x pri=%x -", recoveredCanId, pgn, dst, src, pri);

    for (int i = 0 ; i < bufLen ; i++) {
        fprintf(stdout," %02x", (unsigned)buf[i]);
    }
    fprintf(stdout,"\n");
}

int main(int argc, char* argv[]) 
{
    char* baudNum;
    CanDrvBaudrate baud;
    bool baudSelected = FALSE;

    int c;

    // Certain CanEvents functions are not safely reentrant.
    // For example, when using j1939, it's not safe for one thread to be
    // sending messages while another thread is executing CANEV_processCan.
    // 
    // The library allows you to specify a pthread mutex using CANEV_setMutex,
    // which renders the library multi-thread-safe.
    //
    // This sample application is single-threaded, so it's not strictly
    // necessary to set up this mutex, but we'll do it anyway to show how
    // it is done.
    pthread_mutex_t canMutex;  // normally would probably be a global variable
    pthread_mutex_init(&canMutex, NULL);
    CANEV_setMutex(&canMutex);

    // This is the structure used to configure the CAN stack.
    // CANEV_configInit must be called to provide defaults for 
    // all fields.

    CANEV_Config canConfig;
    CANEV_configInit(&canConfig) ;

    // These configuration flags tell the CANEV module whether
    // to report raw CAN packets, and whether to run the j1939 
    // stack.  While this sample only turns on one at a time, 
    // you can turn on both at once.
    canConfig.raw.enabled = TRUE;
    canConfig.j1939.enabled = FALSE;

    // This config entry tells the CANEV code to call rawFrameHandler
    // whenever a raw frame arrives.  It is only called if the 
    // canConfig.raw.enabled flag is TRUE.
    canConfig.raw.canFrameHandler = rawFrameHandler;

    // Similarly, this config entry tells the CANEV code to call 
    // j1939MessageHandler when a j1939 message is received.
    canConfig.j1939.messageHandler = j1939MessageHandler;

    // Other configuration is set up after we deal with the command
    // line arguments.


    while (1)
    {
        int optionIndex = 0;

        c = getopt_long(argc, argv, "i:b:jsf", longOptions, &optionIndex);

        if (c == -1)
            break;

        switch (c) 
        {
        case 0:
            // if the option selected sets a flag, do nothing
            if (longOptions[optionIndex].flag != 0)
                break;
            fprintf(stdout,"option %s", longOptions[optionIndex].name);
            if (optarg)
                fprintf(stdout," with arg %s", optarg);
            break;
        case 'i':
            // updates CAN interface variables to user selection
            if (strcmp(optarg, "0") == 0) 
            {
                canIfc = DRV_CAN_0;
            } 
            else if (strcmp(optarg, "1") == 0) 
            {
                canIfc = DRV_CAN_1;
            } 
            else 
            {
                fprintf(stderr, "Invalid CAN interface selected.\n");
                printUsage();

                exit(1);

            }

            break;
        case 'b':
            // updates CAN baudrate variables to user selection
            baudSelected = TRUE;
            if (strcmp(optarg, "250") == 0) 
            {
                baud = DRV_CAN_BR_250KBPS;
                baudNum = optarg;
            } 
            else if (strcmp(optarg, "500") == 0) 
            {
                baud = DRV_CAN_BR_500KBPS;
                baudNum = optarg;
            } 
            else if (strcmp(optarg, "1000") == 0) 
            {
                baud = DRV_CAN_BR_1MBPS;
                baudNum = optarg;
            } 
            else 
            {
                // invalid baudrate was selected, inform the user and exit
                fprintf(stderr, "Invalid baudrate\n");
                printUsage();

                exit(1);
            }

            break;
        case 'j':
            // enables J1939 and disables raw protocol if selected
            canConfig.j1939.enabled = TRUE;
            canConfig.raw.enabled = FALSE;

            break;
        case 's':
            // enables option to send periodic CAN messages
            sendEnabled = TRUE;

            break;
        case 'f':
            // enables filtering
            filtering = TRUE;

            break;
        case '?':
            printUsage();
            exit(0);

            break;
        default:
            fprintf(stderr, "Invalid arguments");
            printUsage();
            exit(1);
        }
    }

    // if CAN interface was not specified, inform the user and exit the app
    if (canIfc == DRV_CAN_IF_NONE)
    {
        fprintf(stdout, "Please select a valid CAN interface (0/1)\n");
        printUsage();

        exit(0);
    }

    // if CAN baudrate was not specified, inform the user and exit the app
    if (!baudSelected) 
    {
        fprintf(stdout, "Please select a valid baudrate(250kbps/500/kbps/1mbps)\n");
        printUsage();

        exit(0);
    }

    // fill in the rest of the configuration structure, which was initialized 
    // at the top of the function.

    // set the bus baud rate.
    canConfig.baudrate = baud;

    const int numFilters = 2;
    CAN_CanFilter filters[numFilters];

    // If filtering was enabled on the command line, set up the filters in
    // the config.
    if (filtering) 
    {
        filters[0].canId = 0x18FFBC32;
        filters[0].canMask = 0x1FFFFFFF;  // particular PGN and source/dest
        filters[1].canId = 0x18FFBC19;
        filters[1].canMask = 0x00FFFF00;  // PGN filtering

        canConfig.canFilters = filters;
        canConfig.numCanFilters = numFilters;
    }

    // CANEV_init connects to the CAN device and prepares to start 
    // reading from and writing to it.

    if ( OK != CANEV_init(canIfc, &canConfig) )
    {
        fprintf(stderr, "failed to initialise CAN interface.\n") ;
        exit(1) ;
    }

    fprintf(stdout, "CAN has been configured: can0@%sKbps...\n\r", baudNum);

    // CAN is properly configured at this point
    // we can now start using sockets

    fprintf(stdout, "Monitoring can%d...\n\r\n\r", canIfc);


    time_t lastSentTime = time(NULL);


    // A pointer to this status value is passed to the API that 
    // sends j1939 messages.  The stack will update it to
    // J1939_SEND_INPROCESS, J1939_SEND_FAILED, J1939_SEND_DONE
    // as it handles the outgoing message.
    //
    // You are allowed to pass NULL and ignore status.  However,
    // if you are transmitting multiframe j1939 messages, you are
    // responsible for making sure the buffer you send stays 
    // stable until the status is _DONE or _FAILED.
    uint8_t j1939TransmitStatus = J1939_SEND_UNSET;

    // keep track of whether we've already printed an in-process
    // notification for j1939 transmission, so we're not printing
    // it every 10ms.
    bool j1939InProcessPrinted = FALSE;


    // this is the main loop.  It will sit forever reading and, optionally,
    // sending messages until you kill the program.

    while(1)
    {
        // Process incoming CAN messages, and transmit pending j1939 messages.
        // Each time CANEV_processCan is called it will read all available 
        // data from the CAN device and process it, which includes calling the 
        // handlers defined in the canConfig object we assembled above.

        CANEV_processCan(canIfc);

        if (sendEnabled)
        {
            // transmit a message every 5 seconds or so.
            time_t t = time(NULL);
            if (t - lastSentTime > 5)
            {

                if (canConfig.j1939.enabled) 
                {
                    j1939InProcessPrinted = FALSE;
                    sendSampleJ1939Message(&j1939TransmitStatus);
                }

                if (canConfig.raw.enabled)
                {
                    sendSampleRawMessage();
                }
                lastSentTime = t;
            }


            if (canConfig.j1939.enabled) 
            {
                // j1939 message sending reports its status asynchronously
                // by setting a status value in a location you pass to the
                // CANEV_sendJ1939 message.  This code prints status as it
                // changes.

                switch(j1939TransmitStatus)
                {
                    case J1939_SEND_INPROCESS:
                        // print the in-process message, if we haven't 
                        // already done so.
                        if (!j1939InProcessPrinted) {
                            fprintf(stdout,"j1939 message send in process...\n");
                            j1939InProcessPrinted = TRUE;
                        }
                        break;

                    case J1939_SEND_FAILED:
                        fprintf(stderr,"j1939 message send failed.\n");

                        // stop future status printout.
                        j1939TransmitStatus = J1939_SEND_UNSET;
                        exit(1);
                        break;

                    case J1939_SEND_DONE:
                        fprintf(stderr,"j1939 message successfully sent.\n");

                        // stop future status printout.
                        j1939TransmitStatus = J1939_SEND_UNSET;
                        break;

                    default:
                        break;
                }
            }
        }

        // The J1939 stack must be called every 10ms in order to correctly
        // handle protocol-defined timeouts.
        usleep(10000);
    }

    // not reached.
    return 0;
}

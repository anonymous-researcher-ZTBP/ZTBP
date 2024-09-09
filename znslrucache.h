//#include <stdio.h>
//#include <stdlib.h>

#define NVMEV_DRV_ZNS_NAME "Nvmev_ZNS"
#define NVMEV_ZNS_READ_DEBUG(string, args ...) printk(KERN_INFO "%s: "string, NVMEV_DRV_ZNS_NAME, ##args)
#define CHK_RD_CNT 100000

typedef struct Node {
    int key;
    int value;
    int priority;
    struct Node* prev;
    struct Node* next;

    struct Node* left;
    struct Node* right;
} Node;

typedef struct LRUCache {
    int capacity;
    int size;

    Node* head;
    Node* tail;
    Node* l_head;
    Node* l_tail;

    Node** nodeMap;
} LRUCache;

Node* createNode(int key, int value,int priority);
LRUCache* createLRUCache(int capacity);
void removeNode(Node* node,LRUCache *cache);
void insertToHead(LRUCache* cache, Node* node,int priority);
int get(LRUCache* cache, int key);
void put(LRUCache* cache, int key, int value, int priority);
void freeLRUCache(LRUCache* cache);
void printLRUCache(LRUCache* cache);


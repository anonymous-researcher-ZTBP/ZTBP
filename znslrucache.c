//#include <stdio.h>
//#include <stdlib.h>
#include <linux/slab.h>
#include <linux/kernel.h>
#include "nvmev.h"
//#include "zns_ftl.h"
#include "znslrucache.h"

Node* createNode(int key, int value,int priority) {
    Node* newNode = (Node*)kmalloc(sizeof(Node),GFP_KERNEL);
    newNode->key = key;
    newNode->value = value;

    newNode->prev = NULL;
    newNode->next = NULL;
    newNode->left = NULL;
    newNode->right = NULL;

    newNode->priority = priority;

    return newNode;
}

LRUCache* createLRUCache(int capacity) {
    int i;
    LRUCache* cache = (LRUCache*)kmalloc(sizeof(LRUCache),GFP_KERNEL);
    cache->capacity = capacity;

    cache->head = NULL;
    cache->tail = NULL;
    cache->l_head = NULL;
    cache->l_tail = NULL;

    cache->size = 0;
    cache->nodeMap = (Node**)kmalloc(capacity * sizeof(Node*),GFP_KERNEL);
    
    for (i = 0; i < capacity; ++i) {
        cache->nodeMap[i] = NULL;
    }
    return cache;
}

void removeNode(Node* node,LRUCache *cache) {

//    NVMEV_ZNS_READ_DEBUG("remove node key =%d, pre key=%d\n",node->key,node->prev->key);
    if (node->prev != NULL) {
        node->prev->next = node->next;
    } else { // Node is head
        node->next->prev = NULL;
	cache->head = node->next;
    }
#if 1
    if(cache->l_head == node){
	if(node->next!=NULL){
		cache->l_head = node->next;
	}else{
		cache->l_head = NULL;
	}
    }
#endif
    if (node->next != NULL) {
        node->next->prev = node->prev;
    } else { // Node is tail
        node->prev->next = NULL;
	cache->tail = node->prev;
    }
}

void insertToHead(LRUCache* cache, Node* node,int priority) {
    if(cache->head == NULL && cache->tail == NULL && cache->l_head == NULL){
	    if(priority == 1){
		    cache->head = node;
		    node->prev = NULL;

		    cache->tail = node;
		    cache->tail->next = NULL;
	    }else{
		    cache->head = node;
		    cache->head = node;
		    cache->head->prev = NULL;

		    cache->l_head = node;

		    cache->tail = node;
		    cache->tail->next = NULL;
	    }
    }else if(cache->head !=NULL && cache->tail != NULL && cache->l_head != NULL){
	    if(priority == 1){
		    node->next = cache->head;
		    node->prev = NULL;
		    cache->head->prev = node;
		    cache->head = node;
	    }else{
		    if(cache->tail == cache->l_head){

			    if(cache->l_head == cache->head){
				    Node* head = cache->head;
				    Node* l_head = cache->l_head;
				    cache->head->prev = node;
				    node->prev = NULL;
				    node->next = head;

				    cache->head = node;
				    cache->l_head = node;
				    cache->tail = l_head;
				    l_head->next = NULL;

			    }else{

				    Node* l_head = cache->l_head;
				    cache->l_head->prev->next = node;

				    node->next = cache->l_head;
				    node->prev = cache->l_head->prev;
				    cache->l_head = node;
				    cache->tail = l_head;
				    cache->tail->prev = node;
				    l_head->next = NULL;
			    }

		    }else{
			    if(cache->l_head == cache->head){
				Node* head = cache->head;
				Node* l_head = cache->l_head;
				cache->head->prev = node;
				node->prev = NULL;
				node->next = head;

				cache->head = node;
				cache->l_head = node;

			    }else{
				Node *l_head = cache->l_head;
			    	cache->l_head->prev->next = node;
    				node->next = cache->l_head;
    				node->prev = cache->l_head->prev;
    				cache->l_head->prev = node;
    				cache->l_head = node;
			    }
		    }
	    }
    }else if(cache->head !=NULL && cache->tail != NULL && cache->l_head == NULL){
	    if(priority == 1){
		    node->next = cache->head;
		    node->prev = NULL;
		    cache->head->prev = node;
		    cache->head = node;
	    }else{
		    cache->l_head = node;
		    node->prev = cache->tail;
		    node->prev->next = node;
		    cache->tail = node;
		    node->next = NULL;
	    }
    }
}

int get(LRUCache* cache, int key) {
    Node* getNode = cache->nodeMap[key % cache->capacity];
    Node* findNode = NULL;
    if (getNode != NULL){
	Node* rightNode = getNode;
	while(rightNode){
		if (key == rightNode->key){
			findNode = rightNode;
			break;
		}
		rightNode = rightNode->right;
	}
	if(findNode){
		getNode = findNode;
	}else{
		return -1;
	}
    }else{
	    return -1;
    }
    // Move the node to the head
    if (getNode != cache->head && getNode != cache->l_head) {
		if(getNode == cache->l_head){
			NVMEV_ZNS_READ_DEBUG("what????\n");
		}
        removeNode(getNode,cache);
        insertToHead(cache, getNode,getNode->priority);
    }
    return getNode->value;
}
void put(LRUCache* cache, int key, int value, int priority) {
    int index = key % cache->capacity;
    Node* existingNode = cache->nodeMap[index];

    // Prepare to add a new node if it doesn't exist
    if (cache->size >= cache->capacity) {
        // Evict the least recently used node (tail)
        Node* lruNode = cache->tail;
        if (lruNode->prev) lruNode->prev->next = NULL;
        cache->tail = lruNode->prev;

		Node* hashNode;
 		hashNode = cache->nodeMap[lruNode->key%cache->capacity];
		if(hashNode==NULL){
			NVMEV_ZNS_READ_DEBUG("something wrong\n");
			NVMEV_ZNS_READ_DEBUG("index %d,key%d\n",lruNode->key%cache->capacity,lruNode->key);
			printLRUCache(cache);
		}
		if(hashNode->key == lruNode->key){ //index hashing match and replace
			if(hashNode->right != NULL){
				cache->nodeMap[lruNode->key % cache->capacity] = hashNode->right;
				hashNode->left = NULL;
			}else{
				cache->nodeMap[lruNode->key % cache->capacity] = NULL;
			}

		}else{ //not for head index
			   Node* rightNode = hashNode;
			   if(rightNode == NULL){
				NVMEV_ZNS_READ_DEBUG("wrong data strucuture\n");
			}
			while(rightNode){
				if (lruNode->key == rightNode->key){
						if(rightNode->right&&rightNode->left){
							rightNode->left->right = rightNode->right;
							rightNode->right->left = rightNode->left;
						}
					if(rightNode->right == NULL){
						rightNode->left->right = NULL;
					}
					break;
				}
				rightNode = rightNode->right;
			}
		}
		if(lruNode == cache->l_head){
			cache->l_head = NULL;
		}

        kfree(lruNode); // Free the LRU node
        cache->size--;
    }

    // Create and insert the new node at the head
    Node* newNode = createNode(key, value, priority);
    insertToHead(cache, newNode, priority);

    existingNode = cache->nodeMap[index];
    if (existingNode == NULL){
		cache->nodeMap[index] = newNode;
    }
    cache->size++;

    if (existingNode != NULL && existingNode->key != key) {
		if (existingNode->right == NULL){
			existingNode->right = newNode;
			newNode->left = existingNode;
			newNode->right = NULL;
		}else{
			Node* hashlast = existingNode;
			Node* pre_hashlast = NULL;
			while(hashlast){
				pre_hashlast = hashlast;
				hashlast=hashlast->right;
			}
			pre_hashlast->right = newNode;
			newNode->left = pre_hashlast;
			newNode->right = NULL;
		}
    }
}

#define RANGE_1G_SIZE (1ULL * 1024 * 1024 * 1024)  // 1GB
#define RANGE_128_SIZE (1ULL * 1024 * 1024 * 128)  // 128M
#define RANGE_SIZE (1ULL * 1024 * 1024 )  // 1M
#define RANGE_80 (1ULL * 1024 * 40)//80K
#define ALIGNMENT (4 * 1024)  // 4KB
void freeLRUCache(LRUCache* cache) {
    Node* cur;
    cur = cache->head;
    while (cur) {
        Node* next = cur->next;
        kfree(cur);
        cur = next;
    }
    kfree(cache->nodeMap);
    kfree(cache);
}

void printLRUCache(LRUCache* cache) {
#if 1
    int tot_hash = 0;
    Node* cur = cache->head;
    while (cur) {
		if(tot_hash>cache->size){
			NVMEV_ZNS_READ_DEBUG("linking wrong\n");
			break;
		}
			NVMEV_ZNS_READ_DEBUG("(%d,[%d<-- %d-->%d]), ", cur->priority, (cur->prev!=NULL)?cur->prev->key:-1,cur->key, (cur->next!=NULL)?cur->next->key:-1);
			cur = cur->next;
		tot_hash+=1;
    }
    NVMEV_ZNS_READ_DEBUG("\n");
    if(cache->head !=NULL)
	    NVMEV_ZNS_READ_DEBUG("cache->head %d\n",cache->head->key);
    if(cache->l_head !=NULL)
	    NVMEV_ZNS_READ_DEBUG("cache->l_head %d\n",cache->l_head->key);
    if(cache->tail!=NULL)
	    NVMEV_ZNS_READ_DEBUG("cache->tail %d\n",cache->tail->key);
    
    NVMEV_ZNS_READ_DEBUG("cache capa =%d,size=%d\n",cache->capacity,cache->size);
#if 0
    int i;
    int tot_hash=0;
    for (i=0;i<cache->capacity;i++){
	Node* hash_rightmap = cache->nodeMap[i];
	while(hash_rightmap){
                NVMEV_ZNS_READ_DEBUG("(%d, %d), ",i,hash_rightmap->key);
		hash_rightmap = hash_rightmap->right;
		tot_hash +=1;
        }
    }
    NVMEV_ZNS_READ_DEBUG("tot hash cnt %d\n",tot_hash);
#endif
    NVMEV_ZNS_READ_DEBUG("\n");
#endif
}

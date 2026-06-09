#include <cuda_runtime_api.h>
#include <nixl.h>
#include <nixl_descriptors.h>
#include <nixl_params.h>
#include <unistd.h>

#include <algorithm>
#include <cassert>
#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "agent_data.h"
#include "serdes/serdes.h"
#include "stream/metadata_stream.h"

#define NUM_THREADS 2
#define MEM_VAL 0x41

#define LOG                                      \
  std::cout << current_time() << " " << gettid() \
            << " nixl_communicator.cpp:" << __LINE__ << "] "
#define ERR                                      \
  std::cerr << current_time() << " " << gettid() \
            << " nixl_communicator.cpp:" << __LINE__ << "] "
#define FUNC_IN \
  std::cout << current_time() << " " << gettid() << "] " << __func__ << "() IN "
#define FUNC_OUT                                                     \
  std::cout << current_time() << " " << gettid() << "] " << __func__ \
            << "() OUT "

void printParams(const nixl_b_params_t &params, const nixl_mem_list_t &mems) {
  if (params.empty()) {
    std::cout << "Parameters: (empty)\n";
    return;
  }

  std::cout << "Parameters:\n";
  for (const auto &pair : params) {
    std::cout << "  " << pair.first << " = " << pair.second << std::endl;
  }

  if (mems.empty()) {
    std::cout << "Mems: (empty)\n";
    return;
  }

  std::cout << "Mems:\n";
  for (const auto &elm : mems) {
    std::cout << "  " << nixlEnumStrings::memTypeStr(elm) << std::endl;
  }
}

static char *current_time(void) {
  static char now[40];
  struct timespec ts = (struct timespec){0};
  clock_gettime(CLOCK_REALTIME, &ts);

  snprintf(now, 40, "XX:%02ld:%02ld.%06ld ", (ts.tv_sec % 3600) / 60,
           ts.tv_sec % 60, ts.tv_nsec);

  return now;
}

static void show_nixl_opt_args(const std::string name,
                               nixl_opt_args_t *params) {
  std::cout << current_time() << ": Show nixl_opt_args_t(" << name << ")\n";
  for (nixlBackendH *b : params->backends) {
    std::cout << "  params.backends.backendType:" << b->getType() << "\n";
    std::cout << "  params.backends.supportsRemote:" << b->supportsRemote()
              << "\n";
    std::cout << "  params.backends.supportsLocal:" << b->supportsLocal()
              << "\n";
    std::cout << "  params.backends.supportsNotif:" << b->supportsNotif()
              << "\n";
    std::cout << "  params.backends.supportsProgTh:" << b->supportsProgTh()
              << "\n";
  }
  std::cout << "  params.notifMsg:" << params->notifMsg << "\n";
  std::cout << "  params.hasNotif:" << params->hasNotif << "\n";
  std::cout << "  params.skipDescMerge:" << params->skipDescMerge << "\n";
  std::cout << "  params.includeConnInfo:" << params->includeConnInfo << "\n";
  std::cout << "  params.ipAddr:" << params->ipAddr << "\n";
  std::cout << "  params.port:" << params->port << "\n";
  std::cout << "  params.metadataLabel:" << params->metadataLabel << "\n";
}

static const std::string target("target");
static const std::string initiator("initiator");

static const std::string json_string =
    "{\"agent-num\":0, \"CreateDate\":'2025/05/05 12:00:00.000', "
    "\"name\",\"sample\", \"color\":true, \"systemID\":1234, "
    "\"comment\":\"this is for initiator0.\"}";
static const std::vector<size_t> data_sizes = {json_string.length(), 1024, 512,
                                               768};

static void *allocateMemory(size_t size, nixl_mem_t mem_type) {
  assert(mem_type == nixl_mem_t::DRAM_SEG || mem_type == nixl_mem_t::VRAM_SEG);
  if (mem_type == nixl_mem_t::DRAM_SEG) {
    LOG << "Allocate DRAM_SEG\n";
    return std::malloc(size);
  }

  LOG << "Allocate VRAM_SEG\n";
  void *m;
  cudaMalloc(reinterpret_cast<void **>(&m), size);
  return m;
}

static void freeMemory(void *m, nixl_mem_t mem_type) {
  assert(mem_type == nixl_mem_t::DRAM_SEG || mem_type == nixl_mem_t::VRAM_SEG);
  if (mem_type == nixl_mem_t::DRAM_SEG) {
    LOG << "Free DRAM_SEG\n";
    free(m);
    return;
  }
  LOG << "Free VRAM_SEG\n";
  cudaFree(m);
}

static std::vector<std::shared_ptr<void>> initMem(
    nixlAgent &agent, nixl_reg_dlist_t &memories, nixl_opt_args_t *extra_params,
    uint8_t base_val, std::vector<size_t> sizes,
    const std::string &first_message, std::string role, nixl_mem_t mem_type) {
  std::vector<std::shared_ptr<void>> addrs;

  for (int i = 0; i < sizes.size(); i++) {
    // 固定値で埋め、i==0のときはfirst_messageを埋め込む
    int size = sizes[i];
    uint8_t val = 0;
    if (i != 0 && base_val) val = base_val + i;
    std::unique_ptr<uint8_t[]> data = std::make_unique<uint8_t[]>(size);
    std::fill_n(data.get(), size, val);
    if (i == 0 && base_val) {
      memcpy(data.get(), first_message.c_str(), size);
    }

    // メモリ領域を作成してdataをコピー
    auto memory =
        std::shared_ptr<void>(allocateMemory(size, mem_type),
                              [mem_type](void *m) { freeMemory(m, mem_type); });
    if (mem_type == nixl_mem_t::DRAM_SEG) {
      memcpy(memory.get(), data.get(), size);
    } else {
      cudaMemcpy(memory.get(), data.get(), size, cudaMemcpyHostToDevice);
    }
    data.reset();

    std::string meta = role + std::to_string(i);
    memories.addDesc(nixlBlobDesc((uintptr_t)(memory.get()), size, 0, meta));

    addrs.push_back(memory);
  }
  agent.registerMem(memories, extra_params);

  return addrs;
}

static bool checkMem(std::vector<std::shared_ptr<void>> &addrs,
                     std::vector<size_t> sizes, int base_val,
                     nixl_mem_t mem_type) {
  if (addrs.size() != sizes.size()) return false;

  bool result = true;
  int num = sizes.size();

  LOG << "Check memories:\n";

  auto memory = addrs[0];
  size_t size = sizes[0];
  std::unique_ptr<uint8_t[]> data = std::make_unique<uint8_t[]>(size);
  // auto data = new uint8_t[size];
  if (mem_type == nixl_mem_t::DRAM_SEG) {
    memcpy(data.get(), memory.get(), size);
  } else {
    cudaMemcpy(data.get(), memory.get(), size, cudaMemcpyDeviceToHost);
  }
  std::string a((char *)data.get(), size);
  LOG << "first message = " << a << "\n";
  data.reset();

  for (int i = 1; i < num; i++) {
    size_t size = sizes[i];
    auto memory = addrs[i];
    auto data = new uint8_t[size];
    if (mem_type == nixl_mem_t::DRAM_SEG) {
      memcpy(data, memory.get(), size);
    } else {
      cudaMemcpy(data, memory.get(), size, cudaMemcpyDeviceToHost);
    }

    uint8_t val = (base_val == 0) ? 0 : base_val + i;
    for (int j = 0; j < size; j++) {
      if (data[j] != val) result = false;
    }
    delete[] data;
  }
  return result;
}

static void targetThreadRead(nixlAgent &agent, nixl_opt_args_t *extra_params,
                             nixl_mem_t mem_type) {
  nixl_status_t ret;

  LOG << "agent.getLocalMD()\n";
  nixl_blob_t tgt_metadata;
  agent.getLocalMD(tgt_metadata);

  LOG << "Wait for remote notif\n";
  nixlSerDes remote_serdes;
  std::string remote_agent_name;
  nixl_notifs_t notifs;
  do {
    // spin lock
    ret = agent.getNotifs(notifs, extra_params);
    if (notifs.size() == 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
  } while (ret != NIXL_SUCCESS || notifs.size() == 0);

  LOG << "Process notifs\n";
  for (auto iter = notifs.begin(); iter != notifs.end(); iter++) {
    LOG << "Remote Agent Name: " << iter->first << "\n";
    remote_agent_name = iter->first;

    if (notifs[remote_agent_name].empty()) {
      ERR << "Get Notifs but empty.\n";
      exit(-1);
    }
    LOG << "Desirialize remote's notif\n";
    for (const auto &notif : notifs[remote_agent_name]) {
      auto delim_pos = notif.find('|');
      std::string ip = notif.substr(0, delim_pos);
      std::string real_message = notif.substr(delim_pos + 1);
      if (ip != "") {
        LOG << "Received notif from IP: " << ip << "\n";
      }
      remote_serdes.importStr(real_message);
    }

    LOG << "So, as here, target knows remotes memory info(num and size)!\n";
    LOG << "Verify Deserialized Remote's Desc List\n";
    nixl_reg_dlist_t remote_memory_ucx(&remote_serdes);
    remote_memory_ucx.print();
    std::vector<size_t> sizes;
    for (int i = 0; i < remote_memory_ucx.descCount(); i++) {
      sizes.push_back(remote_memory_ucx[i].len);
    }

    LOG << "Now, Target Memory Allocate.\n";
    nixl_reg_dlist_t local_memory_ucx(mem_type);
    auto addrs = initMem(agent, local_memory_ucx, extra_params, 0, sizes, "",
                         "target", mem_type);
    local_memory_ucx.print();

    LOG << "Verify Deserialized Target's Desc List\n";
    nixl_xfer_dlist_t xfer_target_ucx = local_memory_ucx.trim();
    xfer_target_ucx.print();
    nixl_xfer_dlist_t xfer_remote_ucx = remote_memory_ucx.trim();
    xfer_remote_ucx.print();

    // Need to do this in a loop with NIXL_ERR_NOT_FOUND
    // UCX AM with desc list is faster than listener thread can recv/load MD
    // with sockets Will be deprecated with ETCD or callbacks
    extra_params->notifMsg = "NoTiFiCaTiOn";
    extra_params->hasNotif = true;
    nixlXferReqH *treq;
    ret = NIXL_SUCCESS;
    LOG << "agent.createXferReq()\n";
    do {
      ret = agent.createXferReq(NIXL_READ, xfer_target_ucx, xfer_remote_ucx,
                                remote_agent_name, treq, extra_params);
    } while (ret == NIXL_ERR_NOT_FOUND);

    if (ret != NIXL_SUCCESS) {
      ERR << "Error creating transfer request " << ret << "\n";
      exit(-1);
    }

    LOG << "Post the request with UCX backend agent.postXferReq()\n";
    ret = agent.postXferReq(treq);

    LOG << "Waiting for completion\n";
    while (ret != NIXL_SUCCESS) {
      ret = agent.getXferStatus(treq);
      assert(ret >= 0);
    }

    LOG << "Sanity Check\n";
    bool rc = checkMem(addrs, sizes, MEM_VAL, mem_type);
    if (!rc) {
      ERR << "UCX Transfer failed, buffers are different\n";
    } else {
      LOG << "Transfer completed and Buffers match with Remote\n";
      LOG << "UCX Transfer Success!!!\n";
    }

    LOG << "Completed Sending Data using UCX backend\n";
    agent.releaseXferReq(treq);

    LOG << "Cleanup\n";
    agent.deregisterMem(local_memory_ucx, extra_params);
    agent.invalidateRemoteMD(remote_agent_name);
  }
}

static void targetThreadWrite(nixlAgent &agent, nixl_opt_args_t *extra_params,
                              nixl_mem_t mem_type) {
  nixl_status_t ret;

  LOG << "agent.getLocalMD()\n";
  nixl_blob_t tgt_metadata;
  agent.getLocalMD(tgt_metadata);

  LOG << "Wait for remote notif\n";
  nixlSerDes remote_serdes;
  std::string remote_agent_name;
  nixl_notifs_t notifs;
  do {
    // spin lock
    ret = agent.getNotifs(notifs, extra_params);
    if (notifs.size() == 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
  } while (ret != NIXL_SUCCESS || notifs.size() == 0);

  LOG << "Process notifs\n";
  for (auto iter = notifs.begin(); iter != notifs.end(); iter++) {
    LOG << "Remote Agent Name: " << iter->first << "\n";
    remote_agent_name = iter->first;

    if (notifs[remote_agent_name].empty()) {
      ERR << "Get Notifs but empty.\n";
      exit(-1);
    }
    LOG << "Desirialize remote's notif\n";
    for (const auto &notif : notifs[remote_agent_name]) {
      auto delim_pos = notif.find('|');
      std::string ip = notif.substr(0, delim_pos);
      std::string real_message = notif.substr(delim_pos + 1);
      if (ip != "") {
        LOG << "Received notif from IP: " << ip << "\n";
      }
      remote_serdes.importStr(real_message);
    }

    LOG << "So, as here, target knows remotes memory info(num and size)!\n";
    LOG << "Verify Deserialized Remote's Desc List\n";
    nixl_reg_dlist_t remote_memory_ucx(&remote_serdes);
    remote_memory_ucx.print();

    LOG << "Now, Target Memory Allocate.\n";
    nixl_reg_dlist_t local_memory_ucx(mem_type);
    auto addrs = initMem(agent, local_memory_ucx, extra_params, MEM_VAL, data_sizes,
                         json_string, "target", mem_type);
    checkMem(addrs, data_sizes, MEM_VAL, mem_type);

    LOG << "Verify Deserialized Target's Desc List\n";
    nixl_xfer_dlist_t xfer_target_ucx = local_memory_ucx.trim();
    xfer_target_ucx.print();
    nixl_xfer_dlist_t xfer_remote_ucx = remote_memory_ucx.trim();
    xfer_remote_ucx.print();

    // Need to do this in a loop with NIXL_ERR_NOT_FOUND
    // UCX AM with desc list is faster than listener thread can recv/load MD
    // with sockets Will be deprecated with ETCD or callbacks
    extra_params->notifMsg = "NoTiFiCaTiOn";
    extra_params->hasNotif = true;
    nixlXferReqH *treq;
    ret = NIXL_SUCCESS;
    LOG << "agent.createXferReq()\n";
    do {
      ret = agent.createXferReq(NIXL_WRITE, xfer_target_ucx, xfer_remote_ucx,
                                remote_agent_name, treq, extra_params);
    } while (ret == NIXL_ERR_NOT_FOUND);

    if (ret != NIXL_SUCCESS) {
      ERR << "Error creating transfer request " << ret << "\n";
      exit(-1);
    }

    LOG << "Post the request with UCX backend agent.postXferReq()\n";
    ret = agent.postXferReq(treq);

    LOG << "Waiting for completion\n";
    while (ret != NIXL_SUCCESS) {
      ret = agent.getXferStatus(treq);
      assert(ret >= 0);
    }

    LOG << "Completed Sending Data using UCX backend\n";
    agent.releaseXferReq(treq);

    LOG << "Cleanup\n";
    agent.deregisterMem(local_memory_ucx, extra_params);
    agent.invalidateRemoteMD(remote_agent_name);
  }
}


static void runTarget(const std::string &ip, int port,
                      nixl_thread_sync_t sync_mode, nixl_mem_t mem_type,
                      bool use_read) {
  FUNC_IN << "args(ip:" << ip << ", port:" << port
          << ", sync_mode:" << (int)sync_mode << ")\n";

  nixlAgentConfig cfg(true, true, port, sync_mode);
  cfg.pthrDelay = 1000 * 1000;  // in us
  nixlAgent agent(target, cfg);

  nixl_b_params_t params = {
      {"num_workers", "1"},
  };
  nixlBackendH *ucx;
  agent.createBackend("UCX", params, ucx);

  nixl_opt_args_t extra_params;
  extra_params.backends.push_back(ucx);
  show_nixl_opt_args("extra_params", &extra_params);

  if (use_read) {
    targetThreadRead(std::ref(agent), &extra_params, mem_type);
  } else {
    targetThreadWrite(std::ref(agent), &extra_params, mem_type);
  }
}

static void initiatorThreadRead(const std::string &target_ip, int target_port,
                                nixl_thread_sync_t sync_mode,
                                nixl_mem_t mem_type,
                                const std::string &initiator_ip) {
  FUNC_IN << "args(" << target_ip << ", port:" << target_port << ")\n";

  LOG << "Setup agent for initiator\n";
  nixlAgentConfig cfg(true, true, 0, sync_mode);
  cfg.pthrDelay = 1000 * 1000;  // in us
  std::string local_agent_name = initiator;
  nixlAgent agent(local_agent_name, cfg);

  LOG << "Setup UCX backend\n";
  nixl_mem_list_t mems;
  nixl_b_params_t params;
  nixlBackendH *ucx;
  agent.getPluginParams("UCX", mems, params);
  agent.createBackend("UCX", params, ucx);
  nixl_opt_args_t extra_params;
  extra_params.backends.push_back(ucx);
  {
    nixl_b_params_t init1;
    nixl_mem_list_t mems1;
    nixl_status_t ret1;
    ret1 = agent.getBackendParams(ucx, mems1, init1);
    printParams(init1, mems1);
  }

  LOG << "Fetch Remote MetaData\n";
  nixl_opt_args_t md_extra_params;
  md_extra_params.ipAddr = target_ip;
  md_extra_params.port = target_port;
  agent.fetchRemoteMD(target, &md_extra_params);

  LOG << "Allocate Memory\n";

  nixl_reg_dlist_t local_memory_ucx(mem_type);
  auto addrs = initMem(agent, local_memory_ucx, &extra_params, MEM_VAL,
                       data_sizes, json_string, initiator, mem_type);
  checkMem(addrs, data_sizes, MEM_VAL, mem_type);
  local_memory_ucx.print();
  agent.sendLocalMD(&md_extra_params);

  LOG << "Sending notificaitons\n";
  nixlSerDes serdes;
  assert(local_memory_ucx.serialize(&serdes) == NIXL_SUCCESS);
  std::string message = serdes.exportStr();
  std::string message_with_ip = initiator_ip + "|" + message;

  extra_params.ipAddr = target_ip;
  extra_params.port = target_port;
  {
    nixl_status_t st_notif;
    do {
      // spin lock
      st_notif = agent.genNotif(target, message_with_ip, &extra_params);
      if (st_notif == NIXL_ERR_NOT_FOUND) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    } while (st_notif != NIXL_SUCCESS);
  }

  LOG << "Waiting for transfering data\n";
  {
    nixl_status_t st_getNotif;
    nixl_notifs_t am_notifs;
    do {
      // spin lock
      st_getNotif = agent.getNotifs(am_notifs, &extra_params);
      if (am_notifs.size() == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    } while (st_getNotif != NIXL_SUCCESS || am_notifs.size() == 0);
  }
  LOG << "Data is transfered.\n";

  nixl_status_t status;
  LOG << "Cleanup LocalMD\n";
  status = agent.invalidateLocalMD(&md_extra_params);
  assert(status == NIXL_SUCCESS);
  show_nixl_opt_args("md_extra_params", &md_extra_params);

  LOG << "Cleanup Memory\n";
  status = agent.deregisterMem(local_memory_ucx, &extra_params);
  assert(status == NIXL_SUCCESS);
  show_nixl_opt_args("extra_params", &extra_params);

  // Sleep to terminate ucx after target ucx terminated.
  std::this_thread::sleep_for(std::chrono::seconds(1));
}

static void initiatorThreadWrite(const std::string &target_ip, int target_port,
                                 nixl_thread_sync_t sync_mode,
                                 nixl_mem_t mem_type,
                                 const std::string &initiator_ip) {
  FUNC_IN << "args(" << target_ip << ", port:" << target_port << ")\n";

  LOG << "Setup agent for initiator\n";
  nixlAgentConfig cfg(true, true, 0, sync_mode);
  cfg.pthrDelay = 1000 * 1000;  // in us
  std::string local_agent_name = initiator;
  nixlAgent agent(local_agent_name, cfg);

  LOG << "Setup UCX backend\n";
  nixl_mem_list_t mems;
  nixl_b_params_t params;
  nixlBackendH *ucx;
  agent.getPluginParams("UCX", mems, params);
  agent.createBackend("UCX", params, ucx);
  nixl_opt_args_t extra_params;
  extra_params.backends.push_back(ucx);
  {
    nixl_b_params_t init1;
    nixl_mem_list_t mems1;
    nixl_status_t ret1;
    ret1 = agent.getBackendParams(ucx, mems1, init1);
    printParams(init1, mems1);
  }

  LOG << "Fetch Remote MetaData\n";
  nixl_opt_args_t md_extra_params;
  md_extra_params.ipAddr = target_ip;
  md_extra_params.port = target_port;
  agent.fetchRemoteMD(target, &md_extra_params);

  LOG << "Allocate Memory\n";

  nixl_reg_dlist_t local_memory_ucx(mem_type);
  auto addrs = initMem(agent, local_memory_ucx, &extra_params, 0,
                       data_sizes, "", initiator, mem_type);
  checkMem(addrs, data_sizes, MEM_VAL, mem_type);
  agent.sendLocalMD(&md_extra_params);

  LOG << "Sending notifications\n";
  nixlSerDes serdes;
  assert(local_memory_ucx.serialize(&serdes) == NIXL_SUCCESS);
  std::string message = serdes.exportStr();
  std::string message_with_ip = initiator_ip + "|" + message;

  extra_params.ipAddr = target_ip;
  extra_params.port = target_port;
  {
    nixl_status_t st_notif;
    do {
      // spin lock
      st_notif = agent.genNotif(target, message_with_ip, &extra_params);
      if (st_notif == NIXL_ERR_NOT_FOUND) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    } while (st_notif != NIXL_SUCCESS);
  }

  LOG << "Waiting for transfering data\n";
  {
    nixl_status_t st_getNotif;
    nixl_notifs_t am_notifs;
    do {
      // spin lock
      st_getNotif = agent.getNotifs(am_notifs, &extra_params);
      if (am_notifs.size() == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    } while (st_getNotif != NIXL_SUCCESS || am_notifs.size() == 0);
  }
  LOG << "Data is transferred.\n";
  LOG << "Sanity Check\n";
  bool rc = checkMem(addrs, data_sizes, MEM_VAL, mem_type);
  if (!rc) {
    ERR << "UCX Transfer failed, buffers are different\n";
  } else {
    LOG << "Transfer completed and Buffers match with Remote\n";
    LOG << "UCX Transfer Success!!!\n";
  }

  nixl_status_t status;
  LOG << "Cleanup LocalMD\n";
  status = agent.invalidateLocalMD(&md_extra_params);
  assert(status == NIXL_SUCCESS);
  show_nixl_opt_args("md_extra_params", &md_extra_params);

  LOG << "Cleanup Memory\n";
  status = agent.deregisterMem(local_memory_ucx, &extra_params);
  assert(status == NIXL_SUCCESS);
  show_nixl_opt_args("extra_params", &extra_params);

  // Sleep to terminate ucx after target ucx terminated.
  std::this_thread::sleep_for(std::chrono::seconds(1));
}


static void runInitiator(const std::string &target_ip, int target_port,
                         nixl_thread_sync_t sync_mode, nixl_mem_t mem_type,
                         bool use_read, const std::string &initiator_ip) {
  FUNC_IN << "args(" << target_ip << ", port:" << target_port << ")\n";
  if (use_read) {
    initiatorThreadRead(target_ip, target_port, sync_mode, mem_type, initiator_ip);
  } else {
    initiatorThreadWrite(target_ip, target_port, sync_mode, mem_type, initiator_ip);
  }
}

int main(int argc, char *argv[]) {
  FUNC_IN << std::endl;

  /** Argument Parsing */
  if (argc != 6 && argc != 7) {
    std::cout << "Enter the required arguments\n";
    std::cout << "  <Role:target,initiator> "
              << "<Target IP> <Target Port> <Local Memory Type:dram,vram)> "
                 "<READ/WRITE> <Initiator IP(Optional)>\n";
    exit(-1);
  }

  std::string role(argv[1]);
  std::string target_ip(argv[2]);
  int target_port = std::stoi(argv[3]);
  std::string local_memory_type(argv[4]);
  std::string connection_type(argv[5]);
  std::string initiator_ip;
  if (argc == 7) {
    initiator_ip = argv[6];
  } else {
    initiator_ip = "";
  }
  bool use_read = connection_type == "READ";

  std::transform(role.begin(), role.end(), role.begin(), ::tolower);
  if (!role.find(initiator) && !role.compare(target)) {
    LOG << "Invalid role. Use 'initiator*' or 'target'. Currently " << role
        << std::endl;
    return 1;
  }

  std::transform(local_memory_type.begin(), local_memory_type.end(),
                 local_memory_type.begin(), ::tolower);
  if (local_memory_type != "vram" && local_memory_type != "dram") {
    LOG << "Invalid local_memory_type. Use 'vram' or 'dram'. Currently "
        << local_memory_type << std::endl;
    return 1;
  }

  nixl_mem_t mem_type =
      local_memory_type == "vram" ? nixl_mem_t::VRAM_SEG : nixl_mem_t::DRAM_SEG;
  LOG << "use_vram=" << local_memory_type << ", mem_type=" << mem_type << "\n";

  /*** End - Argument Parsing */

  auto sync_mode = nixl_thread_sync_t::NIXL_THREAD_SYNC_RW;
  if (role == target)
    runTarget(target_ip, target_port, sync_mode, mem_type, use_read);
  else
    runInitiator(target_ip, target_port, sync_mode, mem_type, use_read, initiator_ip);

  FUNC_OUT << " for role:" << role << std::endl;
  return 0;
}

// Persistent native workers for matched, read-only diagnostic computations.
// This does not change the registered CPU or GPU campaign backend. Callers own
// the pool explicitly; no global workers or additional heavy jobs are started.
class NativeDiagnosticPool {
  public:
    explicit NativeDiagnosticPool(std::size_t count) {
        if(count<1||count>10)throw std::invalid_argument("Diagnostic workers must be between 1 and 10; two CPU threads remain reserved");
        const auto before=std::chrono::steady_clock::now();
        try {
            for(std::size_t index=0;index<count;++index)
                workers_.emplace_back([this,index,count]{worker(index,count);});
        } catch(...) {stop();throw;}
        startupSeconds_=std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count();
    }
    NativeDiagnosticPool(const NativeDiagnosticPool&)=delete;
    NativeDiagnosticPool& operator=(const NativeDiagnosticPool&)=delete;
    ~NativeDiagnosticPool(){stop();}
    std::size_t workers() const{return workers_.size();}
    double startupSeconds() const{return startupSeconds_;}
    void run(std::function<void(std::size_t,std::size_t)> operation) {
        // Simultaneous callers serialize only this shared diagnostic service.
        // Their independent environment locks must be acquired before run().
        std::lock_guard invocation(invocationMutex_);
        std::unique_lock lock(mutex_);
        if(stopping_)throw std::runtime_error("Diagnostic pool has stopped");
        operation_=std::move(operation);failure_=nullptr;remaining_=workers_.size();++generation_;
        start_.notify_all();done_.wait(lock,[this]{return remaining_==0;});
        operation_={};if(failure_)std::rethrow_exception(failure_);
    }
  private:
    void worker(std::size_t index,std::size_t count) {
        std::unique_lock lock(mutex_);std::uint64_t observed=0;
        for(;;){
            start_.wait(lock,[this,observed]{return stopping_||generation_!=observed;});
            if(stopping_)return;observed=generation_;lock.unlock();
            std::exception_ptr failure;
            try {operation_(index,count);}catch(...){failure=std::current_exception();}
            lock.lock();if(failure&&!failure_)failure_=failure;
            if(--remaining_==0)done_.notify_one();
        }
    }
    void stop() noexcept {
        {std::lock_guard lock(mutex_);stopping_=true;start_.notify_all();}
        for(auto& thread:workers_)if(thread.joinable())thread.join();
    }
    std::vector<std::thread> workers_;
    std::mutex invocationMutex_,mutex_;
    std::condition_variable start_,done_;
    std::function<void(std::size_t,std::size_t)> operation_;
    std::exception_ptr failure_;
    std::size_t remaining_{0};std::uint64_t generation_{0};bool stopping_{false};
    double startupSeconds_{0};
};

void bindDiagnosticPool(py::module_& module) {
    py::class_<NativeDiagnosticPool,std::shared_ptr<NativeDiagnosticPool>>(module,"CampaignDiagnosticPool")
        .def(py::init<std::size_t>(),py::arg("workers"))
        .def_property_readonly("workers",&NativeDiagnosticPool::workers)
        .def_property_readonly("startup_seconds",&NativeDiagnosticPool::startupSeconds);
}

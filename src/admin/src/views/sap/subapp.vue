<template>
  <div class="app-container">
    <div class="filter-container">
      <el-button v-waves class="filter-item" type="primary" icon="el-icon-search" @click="handleFilter">Search</el-button>
    </div>

    <el-table
      :key="tableKey"
      v-loading="listLoading"
      :data="list"
      border
      fit
      highlight-current-row
      style="width: 100%;"
      @sort-change="sortChange"
    >
      <el-table-column v-show="false" :label="'subappid'" prop="subappid" sortable="custom" align="center" width="180">
        <template slot-scope="scope">
          <span>{{ scope.row.subappid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'subappsid'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.subappsid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'subappurl'" prop="subappurl" align="center">
        <template slot-scope="scope">
          <span>{{ scope.row.subappurl }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'appid'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.appid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'subappdesc'" class-name="status-col">
        <template slot-scope="scope">
          <span>{{ scope.row.subappdesc }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'status'" class-name="status-col" width="50">
        <template slot-scope="scope">
          <el-tag :type="scope.row.status | statusFilter">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="'CreatedAt'" align="center" width="150">
        <template slot-scope="scope">
          <span>{{ scope.row.createdAt | parseTime('{y}-{m}-{d} {h}:{i}') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'Actions'" align="center" width="200" class-name="small-padding fixed-width">
        <template slot-scope="scope">
          <router-link :to="'/subapps/'+scope.row.subappid+'/instances'" class="link-type">
            <el-button type="primary">
              InstanceList
            </el-button>
          </router-link>
          <el-button type="success" size="mini" @click="handleStart(scope.row)">
            Start
          </el-button>
          <el-button size="mini" type="danger" @click="handleStop(scope.row)">
            Stop
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total>0" :total="total" :page.sync="listQuery.page" :limit.sync="listQuery.limit" @pagination="getList" />

  </div>
</template>

<script>
import { fetchSubappList, fetchSubappListInApp, fetchSubappStatus, startSubapp, stopSubapp } from '@/api/subapp'
import waves from '@/directive/waves' // Waves directive
import { parseTime } from '@/utils'
import Pagination from '@/components/Pagination' // Secondary package based on el-pagination

export default {
  name: 'ComplexTable',
  components: { Pagination },
  directives: { waves },
  filters: {
    statusFilter(status) {
      const statusMap = {
        START: 'success',
        draft: 'info',
        STOP: 'danger'
      }
      return statusMap[status]
    }
  },
  data() {
    return {
      tableKey: 0,
      list: null,
      total: 0,
      listLoading: true,
      listQuery: {
        page: 1,
        limit: 20
      },
      importanceOptions: [1, 2, 3],
      sortOptions: [{ label: 'ID Ascending', key: '+id' }, { label: 'ID Descending', key: '-id' }],
      dialogFormVisible: false,
      dialogStatus: '',
      textMap: {
        update: '编辑',
        create: '创建'
      },
      dialogPvVisible: false,
      pvData: [],
      rules: {
        type: [{ required: true, message: 'type is required', trigger: 'change' }],
        timestamp: [{ type: 'date', required: true, message: 'timestamp is required', trigger: 'change' }],
        title: [{ required: true, message: 'title is required', trigger: 'blur' }]
      },
      downloadLoading: false,
      active: 1,
      innerVisible: false
    }
  },
  created() {
    const appid = this.$route.params.appid
    if (appid) {
      this.getSubappListInApp(appid)
    } else {
      this.getList()
    }

  },
  methods: {
    getList() {
      this.listLoading = true
      fetchSubappList(this.listQuery).then(response => {
        this.list = response.data.rows
        this.total = response.data.count

        this.listLoading = false
          setInterval(this.getSubappStatus(), 10)
      })
    },
    getSubappListInApp(appid) {
      this.listLoading = true
      fetchSubappListInApp(appid, this.listQuery).then(response => {
        this.list = response.data.rows
        this.total = response.data.count

        this.listLoading = false
      })
    },
    handleFilter() {
      this.listQuery.page = 1
      this.getList()
    },
    handleModifyStatus(row, status) {
      this.$message({
        message: '操作成功',
        type: 'success'
      })
      row.status = status
    },
    sortChange(data) {
      const { prop, order } = data
      if (prop === 'id') {
        this.sortByID(order)
      }
    },
    sortByID(order) {
      if (order === 'ascending') {
        this.listQuery.sort = '+id'
      } else {
        this.listQuery.sort = '-id'
      }
      this.handleFilter()
    },
    formatJson(filterVal, jsonData) {
      return jsonData.map(v => filterVal.map(j => {
        if (j === 'timestamp') {
          return parseTime(v[j])
        } else {
          return v[j]
        }
      }))
    },
    getSubappStatus() {
      for (let i = 0; i < this.list.length; i++) {
        const i = this.list[i]
        fetchSubappStatus(i.subappid).then(response => {
          if (response === '1') {
            this.list[i]['status'] = 'START'
          } else {
            this.list[i]['status'] = 'STOP'
          }
        })
      }
    },
    handleStart(row) {
      this.currentSubapp = Object.assign({}, row) // copy obj
      this.$confirm('确认启动？')
        .then(_ => {
          this.start()
        })
        .catch(_ => {})
    },
    start() {
      startSubapp(this.currentSubapp.subappid)
        .then(res => {
          this.$notify({
            title: '成功',
            message: '开始启动',
            type: 'success',
            duration: 2000
          })
          this.dialogFormVisible = false
        })
        .catch(e => {
          this.$notify({
            title: '成功',
            message: '开始启动',
            type: 'danger',
            duration: 2000
          })
          this.dialogFormVisible = false
        })
    },
    handleStop(row) {
      this.currentSubapp = Object.assign({}, row) // copy obj
      this.$confirm('确认停止？')
        .then(_ => {
          this.stop()
        })
        .catch(_ => {})
    },
    stop() {
      stopSubapp(this.currentSubapp.subappid)
        .then(res => {
          this.$notify({
            title: '成功',
            message: '开始停止',
            type: 'success',
            duration: 2000
          })
          this.dialogFormVisible = false
        })
        .catch(e => {
          this.$notify({
            title: '成功',
            message: '开始停止',
            type: 'danger',
            duration: 2000
          })
          this.dialogFormVisible = false
        })
    }
  }
}
</script>
<style lang="scss">
  .el-dialog{
    width: 70%;
    margin: 20px auto;
    margin-top: 20px !important;
  }
</style>

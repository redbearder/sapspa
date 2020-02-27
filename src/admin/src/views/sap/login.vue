<template>
  <div class="app-container">
    <div class="filter-container">
      <el-button class="filter-item" style="margin-left: 10px;" type="primary" icon="el-icon-edit" @click="handleCreate">
        Create Login
      </el-button>
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
      <el-table-column v-show="false" :label="'loginid'" prop="loginid" sortable="custom" align="center" width="180">
        <template slot-scope="scope">
          <span>{{ scope.row.loginid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'SID'" class-name="status-col" width="150">
        <template slot-scope="scope">
          <span>{{ scope.row.subapp.subappsid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'username'" prop="username" align="center">
        <template slot-scope="scope">
          <span>{{ scope.row.username }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'password'" class-name="status-col">
        <template slot-scope="scope">
          <span>{{ scope.row.password }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'client'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.client }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'CreatedAt'" align="center" width="150">
        <template slot-scope="scope">
          <span>{{ scope.row.createdAt | parseTime('{y}-{m}-{d} {h}:{i}') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'Actions'" align="center" width="200" class-name="small-padding fixed-width">
        <template slot-scope="scope">
          <el-button type="primary" size="mini" @click="handleUpdate(scope.row)">
            编辑
          </el-button>
          <el-button size="mini" type="danger" @click="handleDelete(row,'deleted')">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total>0" :total="total" :page.sync="listQuery.page" :limit.sync="listQuery.limit" @pagination="getList" />

    <el-dialog :title="textMap[dialogStatus]" :visible.sync="dialogFormVisible">
      <el-form ref="dataForm" :rules="rules" :model="newlogin" label-position="right" label-width="100px">
        <el-form-item v-show="false" :label="'LoginID'" prop="loginid">
          <el-input v-model="newlogin.loginid" />
        </el-form-item>
        <el-form-item :label="'username'" prop="username">
          <el-input v-model="newlogin.username" />
        </el-form-item>
        <el-form-item :label="'password'" prop="password">
          <el-input v-model="newlogin.password" />
        </el-form-item>
        <el-form-item :label="'client'" prop="client">
          <el-input v-model="newlogin.client" />
        </el-form-item>

        <el-form-item label="SID">
          <el-select v-model="newlogin.subappid" placeholder="SID">
            <el-option
              v-for="s in subapplist"
              :key="s.subappid"
              :label="s.subappsid"
              :value="s.subappid"
            />
          </el-select>
        </el-form-item>

      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button @click="dialogFormVisible = false">取消</el-button>
        <el-button type="primary" @click="dialogStatus==='create'?createData():updateData()">确定</el-button>
      </div>
    </el-dialog>

  </div>
</template>

<script>
import { fetchLoginList, createLogin, updateLogin, deleteLogin } from '@/api/saplogin'
import { fetchSubappList, fetchSubappListInApp } from '@/api/subapp'
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
        published: 'success',
        draft: 'info',
        deleted: 'danger'
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
      innerVisible: false,
      newlogin: {
        loginid: undefined,
        username: undefined,
        password: undefined,
        client: undefined,
        subappid: undefined
      }
    }
  },
  created() {
    this.getList()
    this.getSubappList()
  },
  methods: {
    getList() {
      this.listLoading = true
      fetchLoginList(this.listQuery).then(response => {
        this.list = response.data.rows
        this.total = response.data.count

        this.listLoading = false
      })
    },
    getSubappList() {
      this.listLoading = true
      fetchSubappList(this.listQuery).then(response => {
        this.subapplist = response.data.rows
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
    resetTemp() {
      this.newlogin = {
        loginid: undefined,
        username: undefined,
        password: undefined,
        client: undefined,
        subappid: undefined
      }
    },
    handleCreate() {
      this.resetTemp()
      this.dialogStatus = 'create'
      this.isEdit = false
      this.dialogFormVisible = true
      this.$nextTick(() => {
        this.$refs['dataForm'].clearValidate()
      })
    },
    createData() {
      this.$refs['dataForm'].validate((valid) => {
        if (valid) {
          createLogin({ ...this.newlogin })
            .then(res => {
              this.$notify({
                title: '成功',
                message: '创建成功',
                type: 'success',
                duration: 2000
              })
              this.getList()
              this.dialogFormVisible = false
            })
            .catch(e => {
              this.$notify({
                title: '成功',
                message: '创建失败',
                type: 'danger',
                duration: 2000
              })
              this.dialogFormVisible = false
            })
        }
      })
    },
    handleUpdate(row) {
      this.newlogin = Object.assign({}, row) // copy obj
      this.dialogStatus = 'update'
      this.dialogFormVisible = true
    },
    updateData() {
      this.$refs['dataForm'].validate((valid) => {
        if (valid) {
          updateLogin(this.newlogin.loginid, { ...this.newlogin })
            .then(res => {
              this.$notify({
                title: '成功',
                message: '创建成功',
                type: 'success',
                duration: 2000
              })
              this.getList()
              this.dialogFormVisible = false
            })
            .catch(e => {
              this.$notify({
                title: '成功',
                message: '创建失败',
                type: 'danger',
                duration: 2000
              })
              this.dialogFormVisible = false
            })
        }
      })
    },
    handleDelete(row) {
      deleteLogin(row.loginid).then(res => {
        this.$notify({
          title: '成功',
          message: '删除成功',
          type: 'success',
          duration: 2000
        })
        this.getList()
      }).catch(e => {

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

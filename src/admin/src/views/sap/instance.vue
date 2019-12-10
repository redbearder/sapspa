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
      <el-table-column v-show="false" :label="'instid'" prop="instid" sortable="custom" align="center" width="180">
        <template slot-scope="scope">
          <span>{{ scope.row.instid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'instanceid'" class-name="status-col">
        <template slot-scope="scope">
          <span>{{ scope.row.instanceid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'subappid'" prop="subappid" align="center">
        <template slot-scope="scope">
          <span>{{ scope.row.subappid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'instanceno'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.instanceno }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'instancetype'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.instancetype }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'hostid'" class-name="status-col" width="100">
        <template slot-scope="scope">
          <span>{{ scope.row.hostid }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="'CreatedAt'" align="center" width="80">
        <template slot-scope="scope">
          <span>{{ scope.row.createdAt | parseTime('{y}-{m}-{d} {h}:{i}') }}</span>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total>0" :total="total" :page.sync="listQuery.page" :limit.sync="listQuery.limit" @pagination="getList" />

  </div>
</template>

<script>
import { fetchInstanceList } from '@/api/instance'
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
      innerVisible: false
    }
  },
  created() {
    this.getList()
  },
  methods: {
    getList() {
      this.listLoading = true
      fetchInstanceList(this.listQuery).then(response => {
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

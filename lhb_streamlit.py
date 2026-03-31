import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import warnings
import adata
import time

# 导入项目介绍模块
try:
    import streamlit_explan as explan
    IMPORT_EXPLAN = True
except ImportError:
    IMPORT_EXPLAN = False
    st.warning("项目介绍模块导入失败")

# 忽略警告信息
warnings.filterwarnings('ignore')
plt.switch_backend('Agg')

# 创建image文件夹
if not os.path.exists('image'):
    os.makedirs('image')

# 设置页面配置
st.set_page_config(
    page_title="股票分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 安全导入模块
def safe_import():
    """安全导入模块"""
    modules = {}
    import_status = {}
    
    module_configs = [
        ('api_search', ['api_search_draw'], ['api_search_code_draw', 'api_search_name_draw']),
        ('db_search', ['db_search_draw'], ['database_search_name_draw', 'database_search_code_draw']),
        ('lhb', ['find_lhs'], ['search_in_lh', 'find_lhb']),
        ('ths_hot', ['ths_hot'], ['code_draw', 'concept_count']),
        ('db_connect', ['db_connect'], ['db_connect']),
        ('flush_db', ['flush_db'], ['flush_database']),
        ('k_line', ['k_line'], ['draw_kline'])
    ]
    
    for module_name, import_paths, function_names in module_configs:
        try:
            module_dict = {}
            for path in import_paths:
                module = __import__(path)
                for func_name in function_names:
                    if hasattr(module, func_name):
                        module_dict[func_name] = getattr(module, func_name)
                # 对于ths_hot模块，特殊处理main函数
                if module_name == 'ths_hot' and hasattr(module, 'main'):
                    module_dict['main'] = getattr(module, 'main')
            modules[module_name] = module_dict
            import_status[module_name] = True
        except ImportError as e:
            st.warning(f"{module_name}模块导入失败: {e}")
            import_status[module_name] = False
    
    return modules, import_status

MODULES, IMPORT_STATUS = safe_import()

# 缓存函数
@st.cache_data(ttl=1800)
def get_all_stock_codes():
    """获取所有股票代码和名称"""
    try:
        return adata.stock.info.all_code()
    except Exception as e:
        st.error(f"获取股票代码失败: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180)
def get_stock_data_cached(stock_code):
    """缓存股票数据获取"""
    try:
        return adata.stock.market.get_market_min(stock_code)
    except Exception as e:
        return None

def get_stock_name_by_code(stock_code):
    """通过股票代码获取股票名称"""
    try:
        all_codes = get_all_stock_codes()
        if not all_codes.empty:
            result = all_codes[all_codes['stock_code'] == stock_code]
            if not result.empty:
                return result['short_name'].values[0]
    except:
        pass
    return "未知"

def get_stock_code_by_name(short_name):
    """通过股票名称获取股票代码"""
    try:
        all_codes = get_all_stock_codes()
        if not all_codes.empty:
            result = all_codes[all_codes['short_name'] == short_name]
            if not result.empty:
                return result['stock_code'].values[0]
    except:
        pass
    return None

def save_kline_image(df, stock_code, stock_name=""):
    """保存K线图"""
    try:
        fig = MODULES['k_line']['draw_kline'](df, stock_code)
        timestamp = int(time.time())
        filename = f"image/{stock_code}_{timestamp}.png"
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return filename
    except Exception as e:
        st.error(f"保存K线图失败: {str(e)}")
        return None

def get_latest_kline_image(stock_code):
    """获取最新的K线图"""
    try:
        image_files = [f for f in os.listdir('image') if f.startswith(f"{stock_code}_")]
        if image_files:
            image_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]), reverse=True)
            return os.path.join('image', image_files[0])
        return None
    except Exception as e:
        return None

def get_stock_name_from_db(stock_code):
    """从数据库获取股票名称"""
    if not IMPORT_STATUS.get('db_search', False):
        return None
    
    try:
        result = MODULES['db_search']['database_search_code_draw'](stock_code)
        return result if result else None
    except Exception as e:
        st.error(f"数据库查询股票名称失败: {str(e)}")
        return None

def query_stock_data(stock_code, stock_name, data_source):
    """查询股票数据"""
    try:
        # 获取股票名称
        final_stock_name = stock_name
        if not stock_name or stock_name == "未知":
            if data_source == "数据库查询":
                db_stock_name = get_stock_name_from_db(stock_code)
                if db_stock_name:
                    final_stock_name = db_stock_name
            else:
                final_stock_name = get_stock_name_by_code(stock_code)
        
        # 获取股票数据
        k_data = None
        if data_source == "API查询":
            k_data = get_stock_data_cached(stock_code)
        elif data_source == "数据库查询":
            if IMPORT_STATUS.get('db_search', False):
                # 先查询数据库获取股票名称，再获取数据
                db_stock_name = get_stock_name_from_db(stock_code)
                if db_stock_name:
                    final_stock_name = db_stock_name
                    k_data = get_stock_data_cached(stock_code)
            else:
                st.error("数据库查询模块未正确加载")
                return None, None, None
        
        return k_data, final_stock_name, stock_code
    except Exception as e:
        st.error(f"查询股票数据失败: {str(e)}")
        return None, None, None

def display_stock_info(k_data, stock_code, stock_name, data_source):
    """股票信息"""
    if k_data is not None and not k_data.empty:
        current_price = k_data.iloc[-1]['price']
        current_change = k_data.iloc[-1]['change']
        current_change_pct = k_data.iloc[-1]['change_pct']
        
        st.info(f"""
        **股票信息:**
        - 股票代码: {stock_code}
        - 股票名称: {stock_name}
        - 当前价格: {current_price:.2f}
        - 涨跌额: {current_change:+.2f}
        - 涨跌幅: {current_change_pct:+.2f}%
        - 数据源: {data_source}
        """)

def handle_stock_query(stock_code, short_name):
    """处理股票查询和K线图绘制"""
    st.header("📊 股票查询与K线图")
    
    if not IMPORT_STATUS.get('k_line', False):
        st.error("K线图模块未正确加载，无法使用此功能")
        return
    
    # 数据源选择
    data_source = st.radio(
        "选择查询方式",
        ["API查询", "数据库查询"],
        horizontal=True
    )
    
    if data_source == "数据库查询" and not IMPORT_STATUS.get('db_connect', False):
        st.warning("⚠️ 数据库连接模块未正确加载，请先测试数据库连接")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("通过股票代码查询", type="primary", disabled=not stock_code):
            if stock_code:
                with st.spinner("正在查询股票数据..."):
                    k_data, final_stock_name, final_code = query_stock_data(stock_code, "未知", data_source)
                    if k_data is not None:
                        save_kline_image(k_data, final_code, final_stock_name)
                        st.session_state.query_result = k_data
                        st.session_state.query_stock_code = final_code
                        st.session_state.query_stock_name = final_stock_name
                        st.session_state.query_source = data_source
                        st.success("查询成功！")
                        display_stock_info(k_data, final_code, final_stock_name, data_source)
                    else:
                        st.error("查询失败，请检查股票代码是否正确")
    
    with col2:
        if st.button("通过股票名称查询", type="primary", disabled=not short_name):
            if short_name:
                with st.spinner("正在查询股票数据..."):
                    found_code = get_stock_code_by_name(short_name)
                    if found_code:
                        k_data, final_stock_name, final_code = query_stock_data(found_code, short_name, data_source)
                        if k_data is not None:
                            save_kline_image(k_data, final_code, final_stock_name)
                            st.session_state.query_result = k_data
                            st.session_state.query_stock_code = final_code
                            st.session_state.query_stock_name = final_stock_name
                            st.session_state.query_source = data_source
                            st.success("查询成功！")
                            display_stock_info(k_data, final_code, final_stock_name, data_source)
                        else:
                            st.error("获取股票数据失败")
                    else:
                        st.error("未找到相关股票，请检查股票名称是否正确")
    
    # 显示K线图
    if st.session_state.query_result is not None:
        st.subheader("📈 生成K线图")
        if st.button("显示K线图", type="primary"):
            try:
                image_path = get_latest_kline_image(st.session_state.query_stock_code)
                if image_path and os.path.exists(image_path):
                    st.success("K线图生成成功！")
                    st.image(image_path, caption=f"{st.session_state.query_stock_name} ({st.session_state.query_stock_code}) K线图", use_column_width=True)
                    display_stock_info(st.session_state.query_result, st.session_state.query_stock_code, st.session_state.query_stock_name, st.session_state.query_source)
                else:
                    st.error("未找到保存的K线图，请重新查询")
            except Exception as e:
                st.error(f"显示K线图时出现错误: {str(e)}")

def handle_lhb_query(stock_code, short_name):
    """处理龙虎榜查询"""
    st.header("🏆 龙虎榜查询")
    
    if not IMPORT_STATUS.get('lhb', False):
        st.error("龙虎榜查询模块未正确加载，无法使用此功能")
        return
    
    target_code = stock_code if stock_code else short_name
    
    if target_code:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("查询是否在龙虎榜", type="primary"):
                with st.spinner("正在查询龙虎榜数据..."):
                    try:
                        result = MODULES['lhb']['search_in_lh'](target_code)
                        if result is not None and (isinstance(result, pd.DataFrame) and not result.empty or 
                                                  isinstance(result, (list, dict)) and result):
                            st.success("该股票在龙虎榜中!")
                            st.dataframe(result if isinstance(result, pd.DataFrame) else st.json(result))
                        else:
                            st.info("该股票未在龙虎榜中")
                    except Exception as e:
                        st.error(f"查询过程中出现错误: {str(e)}")
        
        with col2:
            if st.button("获取龙虎榜详细数据", type="primary"):
                with st.spinner("正在获取详细数据..."):
                    try:
                        result = MODULES['lhb']['find_lhb'](target_code)
                        if result is not None and (isinstance(result, pd.DataFrame) and not result.empty or 
                                                  isinstance(result, (list, dict)) and result):
                            st.success(f"获取{target_code}龙虎榜数据成功!")
                            st.dataframe(result if isinstance(result, pd.DataFrame) else st.json(result))
                        else:
                            st.info("未找到相关龙虎榜数据")
                    except Exception as e:
                        st.error(f"获取数据过程中出现错误: {str(e)}")
    else:
        st.warning("请输入股票代码或股票名称")

def handle_ths_hot():
    """处理同花顺热榜"""
    st.header("🔥 同花顺热榜")
    
    if not IMPORT_STATUS.get('ths_hot', False):
        st.error("同花顺热榜模块未正确加载，无法使用此功能")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("获取同花顺热榜", type="primary"):
            with st.spinner("正在获取热榜数据..."):
                try:
                    if 'main' in MODULES['ths_hot']:
                        result = MODULES['ths_hot']['main']()
                    else:
                        st.error("热榜功能暂时不可用")
                        return
                    
                    if result is not None and (isinstance(result, pd.DataFrame) and not result.empty or 
                                              isinstance(result, (list, dict)) and result):
                        st.session_state.hot_data = result
                        st.session_state.hot_data_time = pd.Timestamp.now()
                        st.success("热榜数据获取成功!")
                    else:
                        st.error("获取热榜数据失败")
                except Exception as e:
                    st.error(f"获取热榜过程中出现错误: {str(e)}")
    
    # 显示热榜数据
    if hasattr(st.session_state, 'hot_data') and st.session_state.hot_data is not None:
        st.subheader("📊 热榜数据")
        if hasattr(st.session_state, 'hot_data_time') and st.session_state.hot_data_time:
            st.info(f"数据更新时间: {st.session_state.hot_data_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 筛选功能
        if isinstance(st.session_state.hot_data, pd.DataFrame) and not st.session_state.hot_data.empty:
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                price_filter = st.number_input("价格上限", min_value=0.0, max_value=1000.0, value=50.0, step=1.0)
            with col_filter2:
                change_filter = st.number_input("涨跌幅下限(%)", min_value=-20.0, max_value=20.0, value=0.0, step=0.1)
            with col_filter3:
                volume_filter = st.number_input("成交量下限(万)", min_value=0.0, max_value=10000.0, value=0.0, step=100.0)
            
            filtered_data = st.session_state.hot_data.copy()
            
            # 数据类型转换和清理
            try:
                if 'price' in filtered_data.columns:
                    # 确保price列为数值类型
                    filtered_data['price'] = pd.to_numeric(filtered_data['price'], errors='coerce')
                    # 过滤掉NaN值
                    filtered_data = filtered_data[filtered_data['price'].notna() & (filtered_data['price'] <= price_filter)]
                
                if 'change_pct' in filtered_data.columns:
                    # 确保change_pct列为数值类型
                    filtered_data['change_pct'] = pd.to_numeric(filtered_data['change_pct'], errors='coerce')
                    # 过滤掉NaN值
                    filtered_data = filtered_data[filtered_data['change_pct'].notna() & (filtered_data['change_pct'] >= change_filter)]
                
                if 'volume' in filtered_data.columns:
                    # 确保volume列为数值类型
                    filtered_data['volume'] = pd.to_numeric(filtered_data['volume'], errors='coerce')
                    # 过滤掉NaN值
                    filtered_data = filtered_data[filtered_data['volume'].notna() & (filtered_data['volume'] >= volume_filter * 10000)]
            except Exception as e:
                st.warning(f"数据筛选过程中出现警告: {str(e)}")
                # 如果筛选失败，显示原始数据
                st.info("显示原始数据（筛选功能暂时不可用）")
            
            st.success(f"筛选结果: {len(filtered_data)} 只股票")
            st.dataframe(filtered_data, use_container_width=True)
        else:
            st.write(st.session_state.hot_data)
    
    with col2:
        st.subheader("绘制热榜股票K线图")
        hot_stock_code = st.text_input("输入热榜股票代码", key="hot_stock")
        if st.button("绘制K线图", disabled=not hot_stock_code):
            if hot_stock_code:
                with st.spinner("正在绘制K线图..."):
                    try:
                        stock_name = get_stock_name_by_code(hot_stock_code)
                        k_data = get_stock_data_cached(hot_stock_code)
                        if k_data is not None and not k_data.empty:
                            st.success("K线图绘制成功!")
                            fig = MODULES['k_line']['draw_kline'](k_data, hot_stock_code)
                            st.pyplot(fig)
                            display_stock_info(k_data, hot_stock_code, stock_name, "API查询")
                        else:
                            st.error("获取股票数据失败，请检查股票代码是否正确")
                    except Exception as e:
                        st.error(f"绘制过程中出现错误: {str(e)}")
    
    # 概念计数功能
    if hasattr(st.session_state, 'hot_data') and st.session_state.hot_data is not None:
        st.subheader("📊 概念统计")
        if st.button("统计概念出现次数", type="secondary"):
            if not IMPORT_STATUS.get('ths_hot', False):
                st.error("同花顺热榜模块未正确加载")
                return
            
            with st.spinner("正在统计概念..."):
                try:
                    if 'concept_count' in MODULES['ths_hot']:
                        concept_counts = MODULES['ths_hot']['concept_count'](st.session_state.hot_data)
                        if concept_counts is not None and not concept_counts.empty:
                            st.success("概念统计完成!")
                            st.dataframe(concept_counts, use_container_width=True)
                            
                            # 显示统计信息
                            total_concepts = len(concept_counts)
                            total_stocks = concept_counts['count'].sum()
                            st.info(f"统计信息: 共发现 {total_concepts} 个概念，涉及 {total_stocks} 只股票")
                        else:
                            st.warning("未找到概念数据")
                    else:
                        st.error("概念统计功能暂时不可用")
                except Exception as e:
                    st.error(f"概念统计过程中出现错误: {str(e)}")

def handle_database_management():
    """处理数据库管理"""
    st.header("💾 数据库管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("数据库连接测试")
        if st.button("测试数据库连接", type="primary"):
            if not IMPORT_STATUS.get('db_connect', False):
                st.error("数据库连接模块未正确加载")
                return
            
            with st.spinner("正在测试数据库连接..."):
                try:
                    conn = MODULES['db_connect']['db_connect']()
                    if conn:
                        st.success("数据库连接成功!")
                        conn.close()
                    else:
                        st.error("数据库连接失败")
                except Exception as e:
                    st.error(f"连接测试失败: {str(e)}")
    
    with col2:
        st.subheader("数据库更新")
        if st.button("更新数据库", type="secondary"):
            if not IMPORT_STATUS.get('flush_db', False):
                st.error("数据库更新模块未正确加载")
                return
            
            with st.spinner("正在更新数据库..."):
                try:
                    if 'flush_database' in MODULES['flush_db']:
                        result = MODULES['flush_db']['flush_database']()
                        st.success("数据库更新完成!")
                        if result:
                            st.write(result)
                    else:
                        st.error("数据库更新功能暂时不可用")
                except Exception as e:
                    st.error(f"数据库更新失败: {str(e)}")

def main():
    st.title("📈 股票分析系统")
    st.markdown("---")
    
    # 欢迎信息
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True
        if IMPORT_EXPLAN:
            explan.show_welcome_message()
        else:
            st.success("🎉 欢迎使用股票分析系统！")
            st.info("💡 首次使用建议：点击'❓ 快速帮助'查看使用指南，点击'🔧 系统状态'检查模块加载情况。")
    
    # 初始化session_state
    if 'query_result' not in st.session_state:
        st.session_state.query_result = None
        st.session_state.query_stock_code = None
        st.session_state.query_stock_name = None
        st.session_state.query_source = None
        st.session_state.hot_data = None
        st.session_state.hot_data_time = None
    
    # 侧边栏控制
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📋 切换侧边栏", help="点击隐藏或显示侧边栏"):
            if 'sidebar_visible' not in st.session_state:
                st.session_state.sidebar_visible = True
            st.session_state.sidebar_visible = not st.session_state.sidebar_visible
    
    # 系统状态显示
    with col2:
        if st.button("🔧 系统状态", help="查看系统模块加载状态"):
            st.session_state.show_status = not st.session_state.get('show_status', False)
    
    # 快速帮助
    with col3:
        if st.button("❓ 快速帮助", help="查看快速使用指南"):
            st.session_state.show_help = not st.session_state.get('show_help', False)
    
    # 显示UI组件
    if IMPORT_EXPLAN:
        explan.show_ui_components(
            import_status=IMPORT_STATUS,
            show_help=st.session_state.get('show_help', False),
            show_status=st.session_state.get('show_status', False),
            show_welcome=False
        )
    else:
        # 使用备用显示逻辑
        explan.show_fallback_ui(
            import_status=IMPORT_STATUS,
            show_help=st.session_state.get('show_help', False),
            show_status=st.session_state.get('show_status', False)
        )
    
    # 侧边栏功能选择
    if 'sidebar_visible' not in st.session_state or st.session_state.sidebar_visible:
        st.sidebar.title("功能选择")
        function_choice = st.sidebar.selectbox(
            "选择功能模块",
            ["股票查询与K线图", "龙虎榜查询", "同花顺热榜", "数据库管理"]
        )
        
        # 项目介绍
        if IMPORT_EXPLAN and st.sidebar.checkbox("显示项目介绍", value=False):
            explan.show_explan()
    else:
        # 当侧边栏隐藏时，使用下拉菜单
        function_choice = st.selectbox(
            "选择功能模块",
            ["股票查询与K线图", "龙虎榜查询", "同花顺热榜", "数据库管理"]
        )
    
    # 主要输入区域
    col1, col2 = st.columns(2)
    with col1:
        stock_code = st.text_input("股票代码", placeholder="例如: 000001, 600519")
    with col2:
        short_name = st.text_input("股票名称", placeholder="例如: 平安银行, 贵州茅台")
    
    st.markdown("---")
    
    # 根据选择的功能显示不同内容
    if function_choice == "股票查询与K线图":
        handle_stock_query(stock_code, short_name)
    elif function_choice == "龙虎榜查询":
        handle_lhb_query(stock_code, short_name)
    elif function_choice == "同花顺热榜":
        handle_ths_hot()
    elif function_choice == "数据库管理":
        handle_database_management()

if __name__ == "__main__":
    main()

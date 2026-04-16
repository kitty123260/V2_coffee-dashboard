import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# --- 頁面配置 ---
st.set_page_config(page_title="MIS Coffee Club Smart Dashboard", layout="wide")

# --- 1. 數據加載 ---
FILE_NAME = 'MIS_coffee_dataset.xlsx'

@st.cache_data
def load_all_data():
    try:
        sheets = {
            'tx': pd.read_excel(FILE_NAME, sheet_name='transactions'),
            'items': pd.read_excel(FILE_NAME, sheet_name='transaction_items'),
            'prod': pd.read_excel(FILE_NAME, sheet_name='products'),
            'mem': pd.read_excel(FILE_NAME, sheet_name='members'),
            'ws': pd.read_excel(FILE_NAME, sheet_name='workshops'),
            'taste': pd.read_excel(FILE_NAME, sheet_name='taste_profiles'),
            'recipe': pd.read_excel(FILE_NAME, sheet_name='beverage_bean_recipes'),
            'beverages': pd.read_excel(FILE_NAME, sheet_name='coffee_beverages'),
            'bean': pd.read_excel(FILE_NAME, sheet_name='coffee_beans'),
            'flav': pd.read_excel(FILE_NAME, sheet_name='coffee_flavors'),
            'notes': pd.read_excel(FILE_NAME, sheet_name='flavor_notes'),
            'food': pd.read_excel(FILE_NAME, sheet_name='food'),
            'survey': pd.read_excel(FILE_NAME, sheet_name='game_survey_responses'),
            'feedback': pd.read_excel(FILE_NAME, sheet_name='workshop_feedback')

        }
        return sheets
    except Exception as e:
        st.error(f"❌ 數據加載失敗: {e}")
        return None

data = load_all_data()

# --- 繪圖函數定義 (放在 if data: 之前) ---
def draw_radar_chart(member_id, workshop_id):
    # 1. 提取學員數據
    m_data = df_taste[df_taste['member_id'] == member_id].iloc[0]
    m_values = [
        m_data['acidity_score'], 
        m_data['bitterness_score'], 
        m_data['roast_score'], 
        m_data['body_score'],
        m_data['flavor_fruity_score'] * 5 
    ]

# --- 2. 提取課程豆數據 (修正版：經由 feedback 關聯) ---
    try:
        # 【關鍵修正】: 唔再用 df_recipe，改用 df_feedback
        ws_feedback = df_feedback[df_feedback['workshop_id'] == workshop_id]
        
        if ws_feedback.empty:
            return go.Figure().update_layout(title="⚠️ 暫無該課程用豆數據")
            
        # 攞呢個 Workshop 用嘅豆 ID (coffee_bean_id)
        ws_bean_id = ws_feedback['coffee_bean_id'].iloc[0]
        b_data = df_bean[df_bean['coffee_bean_id'] == ws_bean_id].iloc[0]
        
        categories = ['酸度', '苦度', '焙度', '醇厚度', '果味']
        
        # 數據 Mapping 修正
        roast_map = {'light': 1, 'medium': 3, 'dark': 5}
        body_map = {'light': 2, 'medium': 4, 'full': 5}
        
        b_values = [
            b_data['acidity'], 
            b_data['bitterness'], 
            roast_map.get(b_data['roast_level'].lower(), 3),
            body_map.get(b_data['body'].lower(), 3),
            4 # 果味預設
        ]

        fig = go.Figure()
        # (這裡保持你原本畫 Scatterpolar 的 code，但確保變量名正確)
        fig.add_trace(go.Scatterpolar(
            r=m_values + [m_values[0]],
            theta=categories + [categories[0]],
            fill='toself', name='學員偏好', line_color='rgba(255, 75, 75, 0.8)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=b_values + [b_values[0]],
            theta=categories + [categories[0]],
            fill='toself', name='課程用豆', line_color='rgba(31, 119, 180, 0.8)'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True, title=f"風味匹配度分析: {b_data['origin']}"
        )
        return fig
    except Exception as e:
        return go.Figure().update_layout(title=f"⚠️ 圖表生成出錯: {e}")

if data:
    df_tx, df_items, df_prod = data['tx'], data['items'], data['prod']
    df_mem, df_ws, df_taste = data['mem'], data['ws'], data['taste']
    df_recipe, df_bean, df_flav = data['recipe'], data['bean'], data['flav']
    df_notes, df_food, df_survey = data['notes'], data['food'], data['survey']
    df_bev = data['beverages']
    df_feedback = data['feedback']

    st.title("☕ MIS Coffee Club - Staff Smart Dashboard")
    st.markdown("---")

# --- 1. 營運指標 ---
    st.header("📊 1. Operational KPIs (營運關鍵指標)")
    
    # --- 數據預計算 ---
    # A. 計算 AOV (平均客單價)
    total_rev = df_tx['total_amount'].sum()
    total_orders = len(df_tx)
    aov = total_rev / total_orders if total_orders > 0 else 0
    
    # B. 計算 Attach Rate (原本你寫好的邏輯)
    merged_items = df_items.merge(df_prod[['product_id', 'category']], on='product_id')
    order_groups = merged_items.groupby('transaction_id')['category'].unique()
    attach_count = order_groups.apply(lambda x: 'coffee beverage' in x and 'food' in x).sum()
    attach_rate = (attach_count / total_orders * 100) if total_orders > 0 else 0

    # C. 計算高峰時段 (Peak Hour)
    df_tx['transaction_date'] = pd.to_datetime(df_tx['transaction_date'])
    peak_hour = df_tx['transaction_date'].dt.hour.mode()[0]

    # D. 課程帶貨率 (Workshop-to-Bean Conversion)
    # 參加過 Workshop 且買過咖啡豆的會員比例
    ws_members = set(df_feedback['member_id'].unique())
    bean_product_ids = df_prod[df_prod['category'] == 'coffee bean']['product_id'].tolist()
    bean_buyers = set(df_tx[df_tx['transaction_id'].isin(
        df_items[df_items['product_id'].isin(bean_product_ids)]['transaction_id']
    )]['member_id'].unique())
    
    conversion_count = len(ws_members.intersection(bean_buyers))
    ws_conv_rate = (conversion_count / len(ws_members) * 100) if len(ws_members) > 0 else 0

    # --- UI 顯示 (分成兩行) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總營業額 (Total Revenue)", f"${total_rev:,.0f}")
    col2.metric("平均客單價 (AOV)", f"${aov:.1f}")
    col3.metric("總訂單量 (Total Orders)", f"{total_orders:,}")
    col4.metric("活躍會員數", len(df_mem))

    st.write("") # 增加間距

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("連帶銷售率 (Attach Rate)", f"{attach_rate:.1f}%", help="同時購買飲品與食物的比例")
    col6.metric("高峰時段 (Peak Hour)", f"{peak_hour}:00", help="全日訂單量最高的小時")
    col7.metric("課程轉化率", f"{ws_conv_rate:.1f}%", help="參加課程後有買豆的會員比例")
    col8.metric("平均評分 (Avg Rating)", f"{df_feedback['bean_overall_rating'].mean():.1f} / 5.0")

    hourly_sales = df_tx.groupby(df_tx['transaction_date'].dt.hour)['total_amount'].count()
    fig_hour = px.line(x=hourly_sales.index, y=hourly_sales.values, title="全日營運波段圖", labels={'x':'小時', 'y':'訂單量'})
    st.plotly_chart(fig_hour, use_container_width=True)

# --- 1.2 品類轉化漏斗 (Category Funnel) ---
    st.subheader("🎯 產品轉化路徑 (Category Funnel)")
    
    # A. 準備數據：結合 Transaction 同 Items 攞到 Member ID
    df_path = df_items.merge(df_tx[['transaction_id', 'member_id']], on='transaction_id')
    df_path = df_path.merge(df_prod[['product_id', 'category']], on='product_id')

    # B. 定義各階段的會員集合 (Sets)
    # 階段 1: 買過咖啡飲品嘅會員
    bev_mems = set(df_path[df_path['category'] == 'coffee beverage']['member_id'].unique())
    # 階段 2: 買過飲品「且」買過咖啡豆嘅會員
    bean_mems = set(df_path[df_path['category'] == 'coffee bean']['member_id'].unique())
    # 階段 3: 買過飲品、買過豆「且」買過器材/食物嘅會員 (假設類別名係 'food' 或 'equipment')
    # 註：如果你的 CSV 冇 'equipment'，可以用 'food' 做示範
    equip_mems = set(df_path[df_path['category'].isin(['food', 'equipment'])]['member_id'].unique())

    # C. 計算漏斗數值 (計算交集 Intersection)
    s1_count = len(bev_mems)
    s2_count = len(bev_mems.intersection(bean_mems))
    s3_count = len(bev_mems.intersection(bean_mems).intersection(equip_mems))

    # D. 繪製 Plotly 漏斗圖
    fig_funnel = go.Figure(go.Funnel(
        y = ["飲品消費者 (Beverage)", "進階買豆客 (Bean)", "深度愛好者 (Equip/Food)"],
        x = [s1_count, s2_count, s3_count],
        textinfo = "value+percent initial",
        textfont = {"size": 20, "color": "white"},
        marker = {"color": ["#D4A373", "#A98467", "#606C38"]}
    ))

    fig_funnel.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=300
    )

    # 用 Columns 分開圖表同埋解釋文字
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        st.plotly_chart(fig_funnel, use_container_width=True)
    
    with f_col2:
        st.write("#### 💡 營運洞察")
        if s1_count > 0:
            conv_rate = (s2_count / s1_count) * 100
            st.write(f"**飲品到買豆轉化率:** `{conv_rate:.1f}%`")
            if conv_rate < 20:
                st.warning("買豆轉化偏低")
            else:
                st.success("轉化表現理想")

    st.markdown("---")

    # --- 2. 價值耦合 (Golden Pairings) ---
    st.header("🥇 2. Value Coupling & Flavor Science")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🛒 Market Basket Analysis")
        tx_contents = df_items.merge(df_prod, on='product_id').groupby('transaction_id')['name'].apply(list)
        pair_counts = Counter()
        for items in tx_contents:
            drinks = [i for i in items if df_prod[df_prod['name']==i]['category'].iloc[0] == 'coffee beverage']
            foods = [i for i in items if df_prod[df_prod['name']==i]['category'].iloc[0] == 'food']
            for d in drinks:
                for f in foods: pair_counts[(d, f)] += 1
        
        top_p = pd.DataFrame([{'Pair': f"{k[0]} + {k[1]}", 'Count': v} for k, v in pair_counts.most_common(5)])
        st.plotly_chart(px.bar(top_p, x='Count', y='Pair', orientation='h', color_continuous_scale='Oranges', color='Count'), use_container_width=True)

    with c2:
        st.subheader("🔬 動態風味配對 (AI Matcher)")
        coffee_list = df_prod[df_prod['category']=='coffee beverage']['name'].unique()
        selected_drink = st.selectbox("客人點咗邊款咖啡?", coffee_list)
        
        drink_row = df_prod[df_prod['name'] == selected_drink]
        if not drink_row.empty:
            p_id = drink_row['product_id'].iloc[0]
            bev_match = df_bev[df_bev['product_id'] == p_id]
            
            if not bev_match.empty:
                d_id = bev_match['beverage_id'].iloc[0]
                recipe_match = df_recipe[(df_recipe['beverage_id'] == d_id) & (df_recipe['is_default'] == 1)]
                
                if not recipe_match.empty:
                    b_id = recipe_match['coffee_bean_id'].iloc[0]
                    bean_info = df_bean[df_bean['coffee_bean_id'] == b_id].iloc[0]
                    flavs = df_flav[df_flav['coffee_bean_id'] == b_id].merge(df_notes, on='flavor_id')
                    
                    st.write(f"✅ **使用咖啡豆:** {bean_info['origin']}")
                    st.write(f"👅 **風味筆記:** {', '.join(flavs['flavor_name'].tolist())}")
                    
                    # 食物推薦
                    food_details = df_food.merge(df_prod[['product_id', 'name']], on='product_id')

                    roast = bean_info['roast_level']
                    acidity = bean_info['acidity']
                    bitterness = bean_info['bitterness']
                    # 多維度智能篩選
                    if roast == 'dark' or bitterness >= 4:
                        # 深焙/苦：搵甜、rich、cream 嘅嘢平衡
                        rec_pool = food_details[(food_details['is_sweet'] == 1) | (food_details['is_rich'] == 1)]
                        reason = "呢款咖啡味道較重，推薦搭配 **甜度高或質地濃郁** 嘅食物嚟中和。"
                    elif acidity >= 4 or any(flavs['category'] == 'fruity'):
                        # 高酸/果香：搵酥脆、牛油感、鹹點
                        rec_pool = food_details[(food_details['is_flaky'] == 1) | (food_details['is_buttery'] == 1) | (food_details['is_savory'] == 1)]
                        reason = "咖啡帶有明亮酸度，搭配 **酥脆或牛油香** 嘅鹹甜點可以提升風味層次。"
                    else:
                        # 平衡型：搵軟熟、濕潤嘅嘢
                        rec_pool = food_details[(food_details['is_soft'] == 1) | (food_details['is_moist'] == 1)]
                        reason = "咖啡口感平衡，推薦搭配 **口感濕潤軟熟** 嘅烘焙產品。"

                    if not rec_pool.empty:
                        # 隨機抽一個
                        suggestion = rec_pool.sample(n=1).iloc[0]
                        st.success(f"🎯 **AI 推薦搭配:** {suggestion['name']}")
                        st.info(f"**推薦原因:** {reason}")
                        
                        # 顯示食物標籤增加專業感 (修正 column 提取邏輯)
                        tag_cols = ['is_sweet', 'is_savory', 'is_flaky', 'is_creamy', 'is_rich']
                        tags = [col.replace('is_','') for col in tag_cols if col in suggestion and suggestion[col] == 1]
                        st.caption(f"💡 食物特性: {' · '.join(tags)}")
                    else:
                        st.write("暫時未有合適嘅配搭建議。")
# --- 智能食物推薦邏輯結束 ---

    st.markdown("---")

    # --- 3. 顧客口味畫像 (Taste DNA) ---
    st.header("🧬 3. Customer Taste DNA")
    search_id = st.number_input("Enter Member ID:", min_value=1, value=1)
    
    # 執行 Taste DNA 邏輯
    member = df_mem[df_mem['member_id'] == search_id]
    profile = df_taste[df_taste['member_id'] == search_id]
    survey = df_survey[df_survey['member_id'] == search_id]

    if not member.empty:
        l, r = st.columns([1, 1])
        with l:
            st.subheader(f"👤 {member['name'].values[0]}")
            if not profile.empty:
                categories = ['Roast', 'Body', 'Acidity', 'Bitterness', 'Fruity', 'Sweet']
                values = [profile['roast_score'].values[0], profile['body_score'].values[0], 
                          profile['acidity_score'].values[0], profile['bitterness_score'].values[0],
                          profile['flavor_fruity_score'].values[0]*5, profile['flavor_sweet_score'].values[0]*5]
                fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#6F4E37'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        with r:
            st.info("**Customer Persona:** " + ("🔥 Dark Roast Fan" if profile['roast_score'].values[0] > 3 else "🍋 Fruity Explorer"))
            st.subheader("🎮 Game Insights")
            if not survey.empty:
                st.write(f"• Texture: {survey['texture_response'].values[0]}")
                st.write(f"• Weather: {survey['weather_response'].values[0]}")
            
            st.subheader("🛍️ Recent History")
            m_tx = df_tx[df_tx['member_id'] == search_id]['transaction_id']
            history = df_items[df_items['transaction_id'].isin(m_tx)].merge(df_prod, on='product_id')['name'].value_counts().head(3)
            st.write(history if not history.empty else "No records")

        # 動態話術
        st.success(f"💬 **Staff Script:** 『見你平時鍾意{survey['texture_response'].values[0] if not survey.empty else '醇厚'}口感，今日不如試吓我哋嘅推薦？』")

    st.markdown("---")

    # ==========================================
    # 4. 深度工作坊策略分析 (AI Workshop Planner)
    # ==========================================
    st.markdown("---")
    st.header("🎓 4. Workshop Strategy")
    
    # 確保讀取 feedback 數據
    df_fb = data.get('feedback', pd.DataFrame()) # 假設你 load_all_data 有讀取 feedback
    
    t1, t2, t3 = st.tabs(["📊 表現洞察", "🎯 精準營銷", "📅 開班建議"])
    
    with t1:
        st.subheader("工作坊成效回顧")
        if not df_fb.empty:
            fb_analysis = df_fb.merge(df_ws, on='workshop_id')
            instructor_perf = fb_analysis.groupby('instructor')['bean_overall_rating'].mean().sort_values(ascending=False)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.write("**🏆 導師滿意度排行**")
                st.dataframe(instructor_perf)
            with c2:
                # 簡單分析：苦味感知過高
                bitter_issues = fb_analysis[fb_analysis['bitterness_perception'] == 'too_high']
                if not bitter_issues.empty:
                    bitter_counts = bitter_issues['name'].value_counts().reset_index()
                    bitter_counts.columns = ['workshop_name', 'total_count']

                    fig = px.bar(
                        bitter_counts, 
                        x='workshop_name', 
                        y='total_count', 
                        title="苦味感知過高嘅課程 (需調整沖煮教學)",
                        labels={'total_count': '投訴人數', 'workshop_name': '課程名稱'},
                        color='total_count',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ 目前學員對苦味感知度良好。")
        else:
            st.info("暫無工作坊回饋數據可供分析。")

    with t2:
        st.subheader("🎯 學員口味配對推薦")
        
        # --- 1. 介面佈局：下拉選單並排 ---
        c_search1, c_search2 = st.columns(2)
        with c_search1:
            selected_member = st.selectbox("選擇會員 (Member ID):", df_mem['member_id'].unique(), key="ws_member_lookup")
        
        # 記憶體鎖定
        if "last_member_id" not in st.session_state or st.session_state.last_member_id != selected_member:
            st.session_state.last_member_id = selected_member
            st.session_state.current_recommendation = None

        m_profile_df = df_taste[df_taste['member_id'] == selected_member]
        
        if not m_profile_df.empty:
            m_profile = m_profile_df.iloc[0]
            st.write(f"👤 **{df_mem[df_mem['member_id'] == selected_member]['name'].iloc[0]}** 嘅口味特徵")
            
            # 顯示指標 (Metric)
            cols = st.columns(4)
            cols[0].metric("酸度偏好", f"{m_profile['acidity_score']}/5")
            cols[1].metric("苦味偏好", f"{m_profile['bitterness_score']}/5")
            cols[2].metric("焙度偏好", f"{m_profile['roast_score']}/5")
            cols[3].metric("果味偏好", f"{(m_profile['flavor_fruity_score']*5):.1f}/5")

            st.divider()

            # --- 2. 核心計算邏輯 (數值差值評分) ---
            if st.session_state.current_recommendation is None:
                all_recs = []
                for _, ws in df_ws.iterrows():
                    try:
                        # 【關鍵修正】: 透過 df_feedback 搵呢個 workshop 用咗邊粒豆
                        # 攞呢個課程對應嘅第一個 feedback 紀錄入面嘅 bean_id
                        ws_feedback_sample = df_feedback[df_feedback['workshop_id'] == ws['workshop_id']]
                        
                        if not ws_feedback_sample.empty:
                            b_id = ws_feedback_sample['coffee_bean_id'].iloc[0]
                            b_data = df_bean[df_bean['coffee_bean_id'] == b_id].iloc[0]
                            
                            # 【計算匹配得分】
                            diff_acidity = abs(m_profile['acidity_score'] - b_data['acidity'])
                            diff_bitter = abs(m_profile['bitterness_score'] - b_data['bitterness'])
                            
                            # 加入焙度 (Roast) 比較會更準 (假設 roast_level 係字串，我哋簡單 mapping 佢)
                            # 你可以根據需要決定加唔加呢部分
                            roast_map = {'light': 1, 'medium': 3, 'dark': 5}
                            b_roast_val = roast_map.get(b_data['roast_level'].lower(), 3)
                            diff_roast = abs(m_profile['roast_score'] - b_roast_val)
                            
                            # 綜合評分 (每點差異扣 10%)
                            score = max(0, int(100 - ((diff_acidity + diff_bitter + diff_roast) * 10)))
                            
                            all_recs.append({'ws': ws, 'score': score, 'bean': b_data})
                    except Exception as e:
                        continue
                    
                if all_recs:
                    # 根據分數最高排序
                    st.session_state.current_recommendation = sorted(all_recs, key=lambda x: x['score'], reverse=True)[0]


            # --- 3. 顯示雷達圖 (深度對比分析) ---
            st.write("### 🔍 深度對比分析")
            ws_options = df_ws['name'].tolist()
            try:
                default_idx = ws_options.index(st.session_state.current_recommendation['ws']['name'])
            except:
                default_idx = 0

            with c_search2:
                compare_ws_name = st.selectbox("選擇對比課程:", ws_options, index=default_idx, key="ws_compare_select")
            
            compare_ws_id = df_ws[df_ws['name'] == compare_ws_name]['workshop_id'].iloc[0]
            st.plotly_chart(draw_radar_chart(selected_member, compare_ws_id), use_container_width=True)

            # --- 4. 顯示精細化推薦結果 (進度條與評分) ---
            st.write("---")
            if st.session_state.current_recommendation:
                rec = st.session_state.current_recommendation
                ws, score, bean = rec['ws'], rec['score'], rec['bean']

                if score >= 85:
                    tag, desc = "🌟 完美契合", f"呢個課程簡直係為你而設！用豆 **{bean['origin']}** 嘅風味同你平時嘅口味有 **{score}%** 相似。"
                elif score >= 65:
                    tag, desc = "🚀 風味進階", f"匹配度 **{score}%**。呢款課程會帶你嘗試比你平時飲開更 **{'酸' if bean['acidity'] > 3 else '濃'}** 嘅風味。"
                else:
                    tag, desc = "🧗 技能解鎖", f"雖然匹配度得 **{score}%**，但係一次絕佳嘅技術挑戰！"

                st.subheader(tag)
                st.success(f"### {ws['name']}")
                
                # 【顯示進度條】
                st.write(f"**AI 風味匹配度:** {score}%")
                st.progress(score / 100)
                st.info(f"**💡 推薦原因：**\n{desc}")
                
                if st.button("🔄 重新分析配對"):
                    st.session_state.current_recommendation = None
                    st.rerun()

# --- 1. 數據加載之後，定義這個函數 ---
def analyze_ws_strategy(df_ws, df_taste, df_feedback, df_bean):
    market_acidity = df_taste['acidity_score'].mean()
    ws_performance = df_feedback.groupby('workshop_id')['bean_overall_rating'].mean()
    
    # --- 新增：計人數 ---
    ws_counts = df_feedback.groupby('workshop_id')['member_id'].count()
    
    recommendations = []
    attendee_list = [] # --- 新增：存儲人數 ---
    
    for _, ws in df_ws.iterrows():
        ws_id = ws['workshop_id']
        rating = ws_performance.get(ws_id, 0)
        
        # --- 新增：獲取人數 (冇人參加就係 0) ---
        count = ws_counts.get(ws_id, 0)
        attendee_list.append(count)
        
        try:
            b_id = df_feedback[df_feedback['workshop_id'] == ws_id]['coffee_bean_id'].iloc[0]
            b_acidity = df_bean[df_bean['coffee_bean_id'] == b_id]['acidity'].iloc[0]
        except:
            b_acidity = None

        if rating == 0:
            msg = "🆕 數據不足：新課程，建議推廣引流班。"
        elif rating > 4.5:
            msg = "🔥 王牌課程：極受歡迎，應考慮加價或增加班次。"
        elif b_acidity is not None and market_acidity > 3.5 and b_acidity < 2.5:
            msg = "⚠️ 風味缺口：會員偏好淺焙酸香，但此課程用豆過深。"
        elif rating < 3.5:
            msg = "🛠️ 內容調整：評分偏低，建議重新設計教學流程。"
        else:
            msg = "✅ 表現穩定：維持現狀。"
            
        recommendations.append(msg)
        
    # --- 修改：回傳兩個 list ---
    return recommendations, attendee_list

# --- 2. 在 Tab 3 (t3) 裡面調用 ---
with t3:
    if not df_feedback.empty and not df_bean.empty:
        # 1. 執行並獲取建議同埋人數 (呢度變咗攞兩個值)
        recs, counts = analyze_ws_strategy(df_ws, df_taste, df_feedback, df_bean)
        
        # 2. 放入 DataFrame
        df_ws_strategy = df_ws.copy()
        df_ws_strategy['策略分析'] = recs
        df_ws_strategy['參加人數'] = counts # --- 新增 ---
        
        # 3. 顯示 (加埋 '參加人數' 入個 list 度)
        st.write("### 📊 課程表現與策略表")
        st.dataframe(
            df_ws_strategy[['name', 'instructor', '參加人數', '策略分析']], 
            use_container_width=True,
            hide_index=True
        )
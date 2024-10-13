import io
import numpy as np
import trimesh

class CustomMesh:
    def __init__(self):
        self.vertices = [] # 顶点坐标列表
        self.faces = [] # 面片列表，每个面片是一个顶点索引列表，面的顶点按照逆时针排列
        self.normals = [] # 法向量列表
        self.indices = []# 拆分三角形后的面片顶点索引列表

    # 从obj文件读取网格数据，支持多种编码格式
    @classmethod
    def from_obj(cls, file_path):
        mesh = cls()
        encodings = ['utf-8', 'gbk', 'iso-8859-1', 'ascii', 'gb2312']  # 尝试的编码列表
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    for line in f:
                        if line.startswith('v '):
                            vertex = list(map(float, line.split()[1:4]))
                            mesh.vertices.append(vertex)
                        elif line.startswith('f '):
                            face = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
                            mesh.faces.append(face)
                break  # 如果成功读取，跳出循环
            except UnicodeDecodeError:
                continue  # 如果出现解码错误，尝试下一种编码
            except Exception as e:
                print(f"Error reading file with {encoding} encoding: {str(e)}")
                continue
        else:
            raise ValueError(f"Unable to read the file {file_path} with any of the attempted encodings.")

        mesh.vertices = np.array(mesh.vertices)
        mesh.calculate_normals()
        mesh.triangulate_face()
        return mesh

    # 计算网格的法向量，使用拉普拉斯算子平滑法线
    def calculate_normals(self):
        # 初始化法向量
        self.normals = np.zeros_like(self.vertices)
        
        # 构建邻接列表，用于存储每个顶点的邻居
        adjacency_list = {i: set() for i in range(len(self.vertices))}
        
        # 遍历每个面，计算面法向量并记录邻接关系
        for face in self.faces:
            if len(face) < 3:
                continue
            v0, v1, v2 = self.vertices[face[0]], self.vertices[face[1]], self.vertices[face[2]]
            normal = np.cross(v1 - v0, v2 - v0)
            
            # 将每个面的法向量加到面上对应的顶点上
            for vertex_index in face:
                self.normals[vertex_index] += normal
            
            # 更新邻接列表，使用集合避免重复
            for i in range(len(face)):
                current_vertex = face[i]
                next_vertex = face[(i + 1) % len(face)]
                adjacency_list[current_vertex].add(next_vertex)
                adjacency_list[next_vertex].add(current_vertex)

        # 归一化初步计算的法线
        lengths = np.linalg.norm(self.normals, axis=1)
        non_zero = lengths > 0
        self.normals[non_zero] = self.normals[non_zero] / lengths[non_zero, np.newaxis]

        # 使用拉普拉斯算子平滑法线
        smoothed_normals = np.zeros_like(self.normals)
        for i, normal in enumerate(self.normals):
            neighbors = adjacency_list[i]
            if neighbors:
                # 取相邻顶点的法向量平均值，与当前顶点法向量平滑
                neighbor_normals = np.mean([self.normals[neighbor] for neighbor in neighbors], axis=0)
                smoothed_normals[i] = (normal + neighbor_normals) / 2  # 平滑计算
            else:
                smoothed_normals[i] = normal

        # 对平滑后的法线进行归一化
        lengths = np.linalg.norm(smoothed_normals, axis=1)
        non_zero = lengths > 0
        self.normals[non_zero] = smoothed_normals[non_zero] / lengths[non_zero, np.newaxis]

    def copy(self):
        new_mesh = CustomMesh()
        new_mesh.vertices = np.copy(self.vertices)
        new_mesh.faces = [face.copy() for face in self.faces]
        new_mesh.normals = np.copy(self.normals)
        new_mesh.triangulate_face()
        return new_mesh

    # 判断网格是否为三角网格
    def judge_is_trimesh(self):
        return 1 if all(len(face) == 3 for face in self.faces) else 0

    # loop细分算法，直接调用trimesh库的subdivide_loop方法
    def subdivide_loop(self):
        # 模拟文件流，利用 trimesh.load 的读取自动转化机制，将 CustomMesh 转换为 trimesh.Trimesh 对象
        obj_data = []
        for v in self.vertices:
            obj_data.append(f"v {v[0]} {v[1]} {v[2]}")
        for f in self.faces:
            face_str = "f " + " ".join(str(f[i] + 1) for i in range(len(f)))
            obj_data.append(face_str)
        obj_string = "\n".join(obj_data)
        obj_stream = io.StringIO(obj_string)
        trimesh_mesh = trimesh.load(obj_stream, file_type='obj')

        # 使用 Loop 算法细分
        subdivided_mesh = trimesh_mesh.subdivide_loop() 
        new_mesh = CustomMesh()
        new_mesh.vertices = np.array(subdivided_mesh.vertices)
        new_mesh.faces = np.array(subdivided_mesh.faces).tolist()
        
        # 重新计算法线
        new_mesh.calculate_normals()

        # 返回新的网格对象
        return new_mesh

    # Catmull-Clark细分算法，自行实现
    def subdivide_catmull_clark(self):
        # 新网格
        new_mesh = CustomMesh()

        # 计算面心
        face_points = []
        for face in self.faces:
            face_vertices = [self.vertices[i] for i in face]
            face_point = np.mean(face_vertices, axis=0)  # 面片顶点的平均值
            face_points.append(face_point)

        # 边类型的判断：
        # 如果有一个边只关联一个面，那么这个边就是边界边，并且这个边的两个顶点都是边界点

        # 计算边心
        edge_map = {}
        edge_points = []
        for face_idx, face in enumerate(self.faces):
            num_vertices = len(face)
            for i in range(num_vertices):
                v1, v2 = face[i], face[(i + 1) % num_vertices]
                edge_key = tuple(sorted((v1, v2)))  # 保证边的顺序一致

                if edge_key not in edge_map:
                    v1_pos, v2_pos = self.vertices[v1], self.vertices[v2]
                    face_point = face_points[face_idx]
                    edge_map[edge_key] = {"count": 1, "face1_point": face_point, "v1_pos": v1_pos, "v2_pos": v2_pos}
                else:
                    # 只有内部边会进入这个分支，在这里处理内部边，计算内部边心
                    edge_map[edge_key]["count"] += 1 # 记录边的出现次数，如果是1，说明是边界边，如果是2，说明是内部边
                    face1_point = edge_map[edge_key]["face1_point"]
                    v1_pos, v2_pos = edge_map[edge_key]["v1_pos"], edge_map[edge_key]["v2_pos"]
                    face2_point = face_points[face_idx]

                    edge_point = (v1_pos + v2_pos + face1_point + face2_point) / 4 # 内部边心 = （顶点1 + 顶点2 + 面心1 + 面心2）/ 4
                    edge_points.append(edge_point)
                    edge_map[edge_key]["idx"] = len(edge_points) - 1 # 更新 edge_map，记录边的顶点索引

        # 遍历 edge_map 处理边界边
        for edge_key, edge_data in edge_map.items():
            if edge_data["count"] == 1:  # 边界边只出现一次
                v1_pos, v2_pos = edge_data["v1_pos"], edge_data["v2_pos"]
                # 计算边界边的边心 (v1_pos + v2_pos) / 2
                edge_point = (v1_pos + v2_pos) / 2
                edge_points.append(edge_point)

                # 更新 edge_map，记录边的顶点索引
                edge_map[edge_key]["idx"] = len(edge_points) - 1

        # 顶点类型的判断：
        # 如果一个顶点关联的面和关联的边的数量相等，那么这个顶点是网格内部点，否则是网格边界点

        # 计算新的顶点位置
        new_vertices = []
        for i, v in enumerate(self.vertices):
            # adjacent_faces：该顶点关联的所有面
            adjacent_faces = [face_idx for face_idx, face in enumerate(self.faces) if i in face]
            # face_avg：关联的面心的平均值
            face_avg = np.mean([face_points[face_idx] for face_idx in adjacent_faces], axis=0) 

            # adjacent_points：该顶点关联的所有顶点
            adjacent_points = []
            for face_idx in adjacent_faces:
                face = self.faces[face_idx]
                for j in range(len(face)):
                    if face[j] == i: # 找到当前顶点在面片中的索引
                        vr, vl = face[(j - 1) % len(face)], face[(j + 1) % len(face)] # 右边和左边的顶点索引
                        if vr not in adjacent_points:
                            adjacent_points.append(vr)
                        if vl not in adjacent_points:
                            adjacent_points.append(vl)
            # edge_avg：关联的边心的平均值
            edge_avg = (1/2) * v + (1/2) * np.mean([self.vertices[point] for point in adjacent_points], axis=0)

            # 处理网格内部点
            if len(adjacent_faces) == len(adjacent_points):
                n = len(adjacent_faces)
                # 原始顶点的位置更新：新顶点 = (均面心 + 2 * 均边心 + (n - 3) * 原顶点) / n
                vertex_point = (face_avg + 2 * edge_avg + (n - 3) * v) / n
                new_vertices.append(vertex_point)
            # 处理网格边界点
            else:
                # 寻找相邻的两个边界点
                # 在edge_map中找到相邻的两个边界点
                boundary_edges = [key for key in edge_map.keys() if i in key and edge_map[key]['count'] == 1]
                boundary_vertices = []
                for edge in boundary_edges:
                    v1, v2 = edge
                    boundary_vertices.append(v1 if v1 != i else v2)
                n = len(boundary_edges)
                vertex_point = (3/4) * v + (1/4) * np.mean([self.vertices[point] for point in boundary_vertices], axis=0)
                new_vertices.append(vertex_point)

        # 更新新网格的顶点
        new_mesh.vertices = np.vstack([new_vertices, edge_points, face_points]) # 将 新顶点、边心、面心 按顺序放入新网格的顶点列表中

        # 一个面心可以对应多个新顶点，一个顶点在这个面中对应两个边心，
        # 根据这个顶点在原来的面中的索引，找出它的上一个顶点，从而找出第一个边心记为 edge_point1，
        # 根据这个顶点在原来的面中的索引，找出它的下一个顶点，从而找出第二个边心记为 edge_point2，
        # 根据逆时针顺序，依次连接 新顶点、edge_point2、face_point、edge_point1，得到新的面片
        for face_idx, face in enumerate(self.faces):
            # face_points[face_idx]是面心的坐标数据
            # len(new_vertices)+len(edge_points)+face_idx是面心在new_mesh.vertices中的索引
            face_point = len(new_vertices) + len(edge_points) + face_idx
            for i in range(len(face)):
                num_vertices = len(face)
                vr = face[(i - 1) % num_vertices]
                v = face[i]
                vl = face[(i + 1) % num_vertices]
                edge_key1 = tuple(sorted((vr, v)))
                edge_key2 = tuple(sorted((v, vl)))
                edge_point1 = len(new_vertices) + edge_map[edge_key1]["idx"] # 边心1的索引
                edge_point2 = len(new_vertices) + edge_map[edge_key2]["idx"] # 边心2的索引
                new_mesh.faces.append([v, edge_point2, face_point, edge_point1])
                
        # 重新计算法线
        new_mesh.calculate_normals()

        return new_mesh

    #拆分三角形
    def triangulate_face(self):
        for face in self.faces:
        # 假设 `face` 是一个包含 n 个顶点的多边形
            v0 = face[0]  # 固定扇形中心点
            for i in range(1, len(face) - 1):
                v1 = face[i]     # 第 i 个顶点
                v2 = face[i + 1] # 第 i+1 个顶点
                self.indices.extend([v0, v1, v2])  # 生成一个三角形


    # 弃用的 Catmull-Clark 算法，虽然这个算法答案不正确，但是细分效果很有趣，故保留
    # def subdivide_catmull_clark(self):
    #     # 新网格
    #     new_mesh = CustomMesh()

    #     # 计算面心
    #     face_points = []
    #     for face in self.faces:
    #         face_vertices = [self.vertices[i] for i in face]
    #         face_point = np.mean(face_vertices, axis=0)  # 面片顶点的平均值
    #         face_points.append(face_point)

    #     # 计算边心
    #     edge_map = {}
    #     edge_points = []
    #     for face_idx, face in enumerate(self.faces):
    #         num_vertices = len(face)
    #         for i in range(num_vertices):
    #             v1, v2 = face[i], face[(i + 1) % num_vertices]
    #             edge_key = tuple(sorted((v1, v2)))  # 保证边的顺序一致

    #             # 如果这条边之前没有计算过
    #             if edge_key not in edge_map:
    #                 v1_pos, v2_pos = self.vertices[v1], self.vertices[v2]
    #                 face_point = face_points[face_idx]
    #                 edge_point = (v1_pos + v2_pos + face_point) / 3  # 两个顶点与面心的平均值
    #                 edge_map[edge_key] = len(edge_points)  # 边对应新的顶点索引
    #                 edge_points.append(edge_point)

    #     # 计算新的顶点位置
    #     new_vertices = []
    #     for i, v in enumerate(self.vertices):
    #         # 相邻面心
    #         adjacent_faces = [face_idx for face_idx, face in enumerate(self.faces) if i in face]
    #         face_avg = np.mean([face_points[face_idx] for face_idx in adjacent_faces], axis=0)

    #         # 相邻边心
    #         adjacent_edges = []
    #         for face_idx in adjacent_faces:
    #             face = self.faces[face_idx]
    #             for j in range(len(face)):
    #                 if face[j] == i:
    #                     v1, v2 = face[j], face[(j + 1) % len(face)]
    #                     edge_key = tuple(sorted((v1, v2)))
    #                     if edge_key in edge_map:
    #                         adjacent_edges.append(edge_map[edge_key])

    #         if adjacent_edges:
    #             edge_avg = np.mean([edge_points[edge_idx] for edge_idx in adjacent_edges], axis=0)

    #             # 原始顶点的位置更新：加权平均
    #             n = len(adjacent_faces)
    #             vertex_point = (face_avg + 2 * edge_avg + (n - 3) * v) / n
    #             new_vertices.append(vertex_point)
    #         else:
    #             new_vertices.append(v)

    #     # 新顶点 = 原始顶点更新 + 面心 + 边心
    #     new_mesh.vertices = np.vstack([new_vertices, face_points, edge_points])

    #     # 生成新的面片，每个原始面片生成 4 个新的面片
    #     new_faces = []
    #     for face_idx, face in enumerate(self.faces):
    #         num_vertices = len(face)
    #         face_point_idx = len(new_vertices) + face_idx

    #         for i in range(num_vertices):
    #             v1, v2 = face[i], face[(i + 1) % num_vertices]
    #             edge_point_idx = len(new_vertices) + len(face_points) + edge_map[tuple(sorted((v1, v2)))]

    #             # 每个原始面片变成 4 个新面片
    #             new_faces.append([v1, edge_point_idx, face_point_idx])
    #             new_faces.append([edge_point_idx, v2, face_point_idx])

    #     new_mesh.faces = new_faces

    #     # 重新计算法线
    #     new_mesh.calculate_normals()

    #     return new_mesh